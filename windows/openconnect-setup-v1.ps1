param([Parameter(Mandatory=$true)][string]$ConfigBase64)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
if ($env:OS -ne 'Windows_NT') { throw 'Run this command on Windows.' }
if (Get-Process -Name 'openconnect-gui' -ErrorAction SilentlyContinue) {
    throw 'Disconnect VPN and exit OpenConnect GUI using File > Quit, then run this command again.'
}
$config = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($ConfigBase64)) | ConvertFrom-Json
$allowed = @('https://oc.tolf.is:4443','https://oc-riga.tolf.is:443','https://oc-us.tolf.is:4443')
if ($allowed -notcontains [string]$config.gateway) { throw 'Invalid TOLF gateway.' }
if ([string]$config.deviceId -notmatch '^[a-f0-9-]{36}$' -or
    [string]$config.username -ne ('tolf-oc-' + ([string]$config.deviceId).Replace('-',''))) {
    throw 'Invalid device identity.'
}
if ([string]$config.name -notmatch '^TOLF (Moscow|Riga|New York) Auto [a-f0-9]{8}$') { throw 'Invalid profile name.' }
$url = [Uri]$config.certificateUrl
if ($url.Scheme -ne 'https' -or $url.Host -ne 'api.tolf.is' -or $url.Port -ne 443 -or
    $url.UserInfo -or $url.Query -or $url.Fragment -or
    $url.AbsolutePath -notmatch '^/oc/access/import/[A-Za-z0-9_-]{43}\.p12$') {
    throw 'Invalid certificate download URL.'
}
$exeCandidates = @()
foreach ($folder in @($env:ProgramW6432,$env:ProgramFiles,${env:ProgramFiles(x86)})) {
    if ($folder) { $exeCandidates += Join-Path $folder 'OpenConnect-GUI\openconnect-gui.exe' }
}
$exe = $exeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (!$exe) { throw 'OpenConnect GUI was not found. Install OpenConnect GUI 1.6.2 first.' }
Add-Type -AssemblyName System.Security
if (!('TolfOpenConnectRsaV1' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Security.Cryptography;
public static class TolfOpenConnectRsaV1 {
    private static byte[] Wrap(byte tag, byte[] value) {
        var output = new List<byte>(); output.Add(tag);
        if (value.Length < 128) output.Add((byte)value.Length);
        else {
            var length = new List<byte>(); int n = value.Length;
            while (n > 0) { length.Insert(0,(byte)(n & 255)); n >>= 8; }
            output.Add((byte)(128 | length.Count)); output.AddRange(length);
        }
        output.AddRange(value); return output.ToArray();
    }
    private static byte[] Integer(byte[] value) {
        int start = 0; while (start < value.Length - 1 && value[start] == 0) start++;
        var bytes = new List<byte>();
        if ((value[start] & 128) != 0) bytes.Add(0);
        for (int i = start; i < value.Length; i++) bytes.Add(value[i]);
        return Wrap(2,bytes.ToArray());
    }
    public static byte[] Export(RSA rsa) {
        RSAParameters p = rsa.ExportParameters(true);
        try {
            var values = new List<byte>(); values.AddRange(new byte[] {2,1,0});
            foreach (byte[] part in new byte[][] {p.Modulus,p.Exponent,p.D,p.P,p.Q,p.DP,p.DQ,p.InverseQ})
                values.AddRange(Integer(part));
            return Wrap(48,values.ToArray());
        } finally {
            foreach (byte[] part in new byte[][] {p.D,p.P,p.Q,p.DP,p.DQ,p.InverseQ})
                if (part != null) Array.Clear(part,0,part.Length);
        }
    }
}
'@
}
function ConvertTo-TolfPem([byte[]]$Bytes,[string]$Label) {
    $base64 = [Convert]::ToBase64String($Bytes)
    $lines = for ($i=0; $i -lt $base64.Length; $i+=64) {
        $base64.Substring($i,[Math]::Min(64,$base64.Length-$i))
    }
    return ('-----BEGIN '+$Label+"-----`n"+($lines -join "`n")+"`n-----END "+$Label+"-----`n")
}
$client = $null; $cert = $null; $rsa = $null; $base = $null; $target = $null
$p12 = $null; $keyDer = $null; $keyBytes = $null; $protected = $null; $created = $false
$registryPath = 'Software\OpenConnect-GUI Team\OpenConnect-GUI'
$profileKey = 'server:' + [string]$config.name
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $client = New-Object Net.WebClient
    try { $p12 = $client.DownloadData($url) }
    catch { throw 'Certificate download failed or expired. Copy a new setup command from the website.' }
    $flags = [Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable -bor
             [Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet
    try { $cert = [Security.Cryptography.X509Certificates.X509Certificate2]::new($p12,[string]$config.password,$flags) }
    catch { throw 'Cannot open the downloaded certificate.' }
    if (!$cert.HasPrivateKey -or $cert.GetNameInfo([Security.Cryptography.X509Certificates.X509NameType]::SimpleName,$false) -ne [string]$config.username) {
        throw 'The certificate does not match this device.'
    }
    $rsa = [Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert)
    if (!$rsa) { throw 'The certificate does not contain an RSA key.' }
    $keyDer = [TolfOpenConnectRsaV1]::Export($rsa)
    $keyPem = ConvertTo-TolfPem $keyDer 'RSA PRIVATE KEY'
    $certPem = ConvertTo-TolfPem $cert.RawData 'CERTIFICATE'
    # Match CryptData::encode(): UTF-8 data and gateway entropy both include NUL.
    $keyBytes = [Text.Encoding]::UTF8.GetBytes($keyPem + [char]0)
    $entropy = [Text.Encoding]::UTF8.GetBytes([string]$config.gateway + [char]0)
    $protected = [Security.Cryptography.ProtectedData]::Protect($keyBytes,$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
    $base = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($registryPath)
    $certHash = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($cert.RawData)).Replace('-','').ToLowerInvariant()
    if ($base.GetSubKeyNames() -contains $profileKey) {
        $existing = $base.OpenSubKey($profileKey)
        try {
            $matches = $existing.GetValue('tolf-device-id') -eq [string]$config.deviceId -and
                       $existing.GetValue('tolf-cert-sha256') -eq $certHash -and
                       $existing.GetValue('server') -eq [string]$config.gateway
        } finally { $existing.Close() }
        if (!$matches) { throw 'A different profile already uses this name. Existing settings were not changed.' }
        Write-Host ('OK: profile already configured: '+[string]$config.name)
        Start-Process -FilePath $exe
        Write-Host 'Select the profile in Server and click Connect.'
        return
    }
    $target = $base.CreateSubKey($profileKey); $created = $true
    $stringValues = @{
        'protocol-name'='anyconnect'; 'username'=''; 'interface-name'=''; 'vpnc-script'='';
        'tolf-device-id'=[string]$config.deviceId; 'tolf-cert-sha256'=$certHash;
        'ca-cert'='@ByteArray()'; 'server-hash'='@ByteArray()'; 'token-str'='@ByteArray()';
        'client-cert'=('@ByteArray('+$certPem+')');
        'client-key'=('@ByteArray(xxxx'+[Convert]::ToBase64String($protected)+')')
    }
    foreach ($name in $stringValues.Keys) { $target.SetValue($name,$stringValues[$name],[Microsoft.Win32.RegistryValueKind]::String) }
    $numberValues = @{'batch'=0;'proxy'=0;'disable-udp'=0;'minimize-on-connect'=0;'reconnect-timeout'=300;'dtls_attempt_period'=25;'server-hash-algo'=0;'token-type'=-1}
    foreach ($name in $numberValues.Keys) { $target.SetValue($name,[int]$numberValues[$name],[Microsoft.Win32.RegistryValueKind]::DWord) }
    # The /server value makes the profile visible. Write it only when complete.
    $target.SetValue('server',[string]$config.gateway,[Microsoft.Win32.RegistryValueKind]::String)
    $target.Flush(); $target.Close(); $target = $null
    Write-Host ('OK: profile created: '+[string]$config.name)
    try { Start-Process -FilePath $exe }
    catch { Write-Host 'Open OpenConnect GUI from its shortcut.' }
    Write-Host 'Select the new profile in Server and click Connect.'
} catch {
    if ($target) { $target.Close(); $target = $null }
    if ($created -and $base) { $base.DeleteSubKeyTree($profileKey,$false) }
    throw
} finally {
    if ($target) { $target.Close() }; if ($base) { $base.Close() }
    if ($rsa) { $rsa.Dispose() }; if ($cert) { $cert.Dispose() }; if ($client) { $client.Dispose() }
    foreach ($bytes in @($p12,$keyDer,$keyBytes,$protected)) {
        if ($null -ne $bytes) { [Array]::Clear($bytes,0,$bytes.Length) }
    }
    $keyPem = $null; $config = $null; $ConfigBase64 = $null
}
