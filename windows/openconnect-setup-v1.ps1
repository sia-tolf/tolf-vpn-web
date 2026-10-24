param([Parameter(Mandatory=$true)][string]$ConfigBase64)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
if ($env:OS -ne 'Windows_NT') { throw 'Run this command on Windows.' }
if ($PSVersionTable.PSVersion -lt [version]'5.1') { throw 'Windows PowerShell 5.1 or newer is required. Install Windows updates before running setup again.' }
$win = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
if ([int]$win.CurrentBuildNumber -lt 10240) { throw 'This Windows version is too old for automatic setup. Use an updated Windows 10 or Windows 11 computer.' }
$net = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction SilentlyContinue
if ($null -eq $net -or [int]$net.Release -lt 461808) { throw '.NET Framework 4.7.2 or newer is required. Install .NET Framework 4.8 from https://dotnet.microsoft.com/download/dotnet-framework/net48 and run setup again.' }
if (Get-Process -Name 'openconnect-gui' -ErrorAction SilentlyContinue) {
    throw 'Disconnect VPN and exit OpenConnect GUI using File > Quit, then run this command again.'
}
$config = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($ConfigBase64)) | ConvertFrom-Json
$allowed = @('https://oc.tolf.is:4443','https://oc-riga.tolf.is:443','https://oc-us.tolf.is:4443','https://oc-us-moscow.tolf.is:4443')
if ($allowed -notcontains [string]$config.gateway) { throw 'Invalid TOLF gateway.' }
if ([string]$config.deviceId -notmatch '^[a-f0-9-]{36}$' -or
    [string]$config.username -ne ('tolf-oc-' + ([string]$config.deviceId).Replace('-',''))) {
    throw 'Invalid device identity.'
}
if ([string]$config.name -notmatch '^TOLF (Moscow|Riga|New York) (Auto|RU|LV|US|YT)$') { throw 'Invalid profile name.' }
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
        // Ephemeral PFX imports use CNG. Set this imported key's export policy
        // before exporting it, as documented by the .NET cryptography team.
        RSACng cng = rsa as RSACng;
        if (cng != null) {
            cng.Key.SetProperty(new CngProperty("Export Policy",
                BitConverter.GetBytes((int)(CngExportPolicies.AllowExport | CngExportPolicies.AllowPlaintextExport)),
                CngPropertyOptions.None));
        }
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
$client = $null; $cert = $null; $rsa = $null;

function ConvertTo-TolfExcludedNetworks($InputNetworks) {
    $result=@()
    foreach($value in @($InputNetworks)){
        if([string]$value -notmatch '^(\d{1,3}\.){3}\d{1,3}/([1-9]|[12]\d|3[0-2])$'){throw 'Invalid IPv4 exclusion.'}
        $parts=([string]$value).Split('/')
        $octets=@($parts[0].Split('.') | ForEach-Object {[int]$_})
        if(@($octets | Where-Object {$_ -gt 255}).Count){throw 'Invalid IPv4 exclusion.'}
        $bits=[int]$parts[1];$canonical=@()
        for($i=0;$i -lt 4;$i++){
            $take=[Math]::Max(0,[Math]::Min(8,$bits-$i*8))
            $mask=if($take -eq 0){0}else{256-[Math]::Pow(2,8-$take)}
            $canonical+=($octets[$i] -band [int]$mask)
        }
        $network=($canonical -join '.')+'/'+$bits
        if($result -notcontains $network){$result+=$network}
    }
    if($result.Count -gt 32){throw 'Maximum 32 excluded networks.'}
    return $result
}
function New-TolfRouteFiles([string[]]$Networks,[string]$DeviceId,[string]$Exe) {
    $defaultScript=Join-Path (Split-Path -Parent $Exe) 'vpnc-script.js'
    if(!(Test-Path -LiteralPath $defaultScript)){throw 'OpenConnect vpnc-script.js was not found.'}
    $identity=$DeviceId+'|'+($Networks -join ',')+'|'+$defaultScript
    $hash=[BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($identity))).Replace('-','').Substring(0,24)
    $directory=Join-Path $env:LOCALAPPDATA ('TOLF\OpenConnect\'+$hash)
    $hookPath=Join-Path $directory 'route-hook.ps1'
    $wrapperPath=Join-Path $directory 'vpnc-wrapper.js'
    $statePath=Join-Path $directory 'routes-state.json'
    $settings=@{networks=@($Networks);state=$statePath} | ConvertTo-Json -Compress
    $settings64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($settings))
    $hook=@'
$ErrorActionPreference='Stop'
$settings=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__SETTINGS__')) | ConvertFrom-Json
function Clear-TolfOwnedRoutes {
    if(!(Test-Path -LiteralPath $settings.state)){return}
    $records=@(Get-Content -LiteralPath $settings.state -Raw | ConvertFrom-Json)
    foreach($record in $records){
        $routes=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix $record.prefix -InterfaceIndex ([int]$record.index) -PolicyStore ActiveStore -ErrorAction SilentlyContinue |
            Where-Object {$_.NextHop -eq $record.gateway -and $_.RouteMetric -eq [int]$record.metric})
        foreach($route in $routes){$route | Remove-NetRoute -Confirm:$false -ErrorAction Stop}
    }
    Remove-Item -LiteralPath $settings.state -Force
}
if($env:reason -eq 'disconnect'){Clear-TolfOwnedRoutes;return}
if($env:reason -ne 'connect'){return}
Clear-TolfOwnedRoutes
$owned=@()
try{
    # Resolve all paths before adding routes or letting the standard script enable VPN routing.
    $plans=@()
    foreach($prefix in $settings.networks){
        $ip=([string]$prefix).Split('/')[0]
        $path=@(Find-NetRoute -RemoteIPAddress $ip -ErrorAction Stop | Where-Object {$null -ne $_.PSObject.Properties['DestinationPrefix']}) | Select-Object -First 1
        if($null -eq $path){throw ('No existing route to '+$prefix)}
        if($env:TUNIDX -and $path.InterfaceIndex -eq [int]$env:TUNIDX){throw ('Existing path already uses VPN for '+$prefix)}
        $plans+=@{prefix=[string]$prefix;index=[int]$path.InterfaceIndex;gateway=[string]$path.NextHop;metric=1}
    }
    foreach($plan in $plans){
        # Keep any pre-existing matching route; never claim or delete another route.
        $existing=@(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix $plan.prefix -InterfaceIndex $plan.index -PolicyStore ActiveStore -ErrorAction SilentlyContinue |
            Where-Object {$_.NextHop -eq $plan.gateway})
        if($existing.Count){continue}
        $null=New-NetRoute -DestinationPrefix $plan.prefix -InterfaceIndex $plan.index -NextHop $plan.gateway -RouteMetric $plan.metric -PolicyStore ActiveStore -ErrorAction Stop
        $owned+=$plan
        ConvertTo-Json -InputObject @($owned) -Compress | Set-Content -LiteralPath $settings.state -Encoding UTF8
        Write-Host ('TOLF: excluded '+$plan.prefix+' via '+$plan.gateway+' interface '+$plan.index)
    }
}catch{
    # Clear routes added during a partially failed attempt, including a state-write failure.
    foreach($plan in $owned){
        Get-NetRoute -AddressFamily IPv4 -DestinationPrefix $plan.prefix -InterfaceIndex $plan.index -PolicyStore ActiveStore -ErrorAction SilentlyContinue |
            Where-Object {$_.NextHop -eq $plan.gateway -and $_.RouteMetric -eq $plan.metric} |
            Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue
    }
    if(Test-Path -LiteralPath $settings.state){Remove-Item -LiteralPath $settings.state -Force}
    throw
}
'@
    $hook=$hook.Replace('__SETTINGS__',$settings64)
    # Read the hook through -Command; do not change the user's execution policy.
    $path64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($hookPath))
    $loader='$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('''+$path64+''')); & ([scriptblock]::Create([IO.File]::ReadAllText($p)))'
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($loader))
    $quotedDefault=ConvertTo-Json -InputObject $defaultScript -Compress
    $wrapper=@'
var shell = new ActiveXObject("WScript.Shell");
var environment = shell.Environment("PROCESS");
var reason = environment("reason");
function hook() {
    return shell.Run('powershell.exe -NoLogo -NoProfile -EncodedCommand __LOADER__', 0, true);
}
if (reason == "connect" && hook() != 0) {
    WScript.Echo("TOLF: cannot preserve excluded routes. VPN routing was not enabled.");
    WScript.Quit(1);
}
var result = shell.Run('cscript.exe //NoLogo "' + __DEFAULT__ + '"', 0, true);
if (reason == "disconnect") {
    if (hook() != 0) result = 1;
} else if (reason == "connect" && result != 0) {
    environment("reason") = "disconnect";
    hook();
    environment("reason") = reason;
}
WScript.Quit(result);
'@
    $wrapper=$wrapper.Replace('__LOADER__',$encoded).Replace('__DEFAULT__',$quotedDefault)
    return @(@{path=$hookPath;content=$hook},@{path=$wrapperPath;content=$wrapper})
}

function New-TolfRemovalCommand([string]$Name,[string]$DeviceId,[string]$Gateway) {
    $template = @'
$ErrorActionPreference='Stop'
if(Get-Process -Name 'openconnect-gui' -ErrorAction SilentlyContinue){throw 'Exit OpenConnect GUI using File > Quit, then run this file again.'}
$name='__NAME__'
$base=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Software\OpenConnect-GUI Team\OpenConnect-GUI',$true)
if($null -eq $base){Write-Host 'Profile already absent.';exit 0}
try{
 $key='server:'+$name
 $profile=$base.OpenSubKey($key)
 if($null -eq $profile){Write-Host 'Profile already absent.';exit 0}
 try{
  if($profile.GetValue('tolf-device-id') -ne '__DEVICE__' -or $profile.GetValue('server') -ne '__GATEWAY__'){throw 'Profile identity changed. Nothing was deleted.'}
 }finally{$profile.Close()}
 Write-Host ('Remove local VPN profile: '+$name)
 Write-Host 'Other profiles and server access will remain unchanged.'
 if((Read-Host 'Type REMOVE to confirm') -cne 'REMOVE'){Write-Host 'Cancelled. Nothing was deleted.';exit 0}
 if(Get-Process -Name 'openconnect-gui' -ErrorAction SilentlyContinue){throw 'OpenConnect GUI is running. Nothing was deleted.'}
 $base.DeleteSubKeyTree($key,$false)
 $base.Flush()
 if($base.GetSubKeyNames() -contains $key){throw 'Profile removal failed.'}
 Write-Host ('OK: removed '+$name)
}finally{$base.Close()}
'@
    $body=$template.Replace('__NAME__',$Name).Replace('__DEVICE__',$DeviceId).Replace('__GATEWAY__',$Gateway)
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($body))
    return [string]::Join(([string][char]13+[char]10),@('@echo off','setlocal DisableDelayedExpansion',('powershell.exe -NoLogo -NoProfile -EncodedCommand '+$encoded),'if errorlevel 1 echo Removal failed. Read the error above.','pause',''))
}

function New-TolfRestoreCommand([string]$ProtectedSnapshot) {
    if($ProtectedSnapshot -notmatch '^[A-Za-z0-9+/=]+$'){throw 'Invalid protected snapshot.'}
    $template=@'
$ErrorActionPreference='Stop'
if(Get-Process -Name 'openconnect-gui' -ErrorAction SilentlyContinue){throw 'Exit OpenConnect GUI using File > Quit, then run Setup again.'}
Add-Type -AssemblyName System.Security
$plain=$null;$base=$null;$target=$null;$created=$false
try{
 try{
  $plain=[Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String('__SNAPSHOT__'),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
 }catch{throw 'This backup can only be restored by the Windows user who created it.'}
 $backup=[Text.Encoding]::UTF8.GetString($plain) | ConvertFrom-Json
 if($backup.name -notmatch '^TOLF (Moscow|Riga|New York) (Auto|RU|LV|US|YT)$'){throw 'Invalid profile backup.'}
 $values=$backup.values
 if(@('https://oc.tolf.is:4443','https://oc-riga.tolf.is:443','https://oc-us.tolf.is:4443','https://oc-us-moscow.tolf.is:4443') -notcontains $values.server){throw 'Invalid gateway.'}
 if($backup.PSObject.Properties['files']){
  $allowedRoot=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'TOLF\OpenConnect\'))
  foreach($file in @($backup.files)){
   $filePath=[IO.Path]::GetFullPath([string]$file.path)
   if(!$filePath.StartsWith($allowedRoot,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($filePath) -notin @('route-hook.ps1','vpnc-wrapper.js')){throw 'Invalid route helper path.'}
   $null=[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($filePath))
   [IO.File]::WriteAllText($filePath,[string]$file.content,[Text.Encoding]::Unicode)
  }
 }
 $key='server:'+$backup.name
 $base=[Microsoft.Win32.Registry]::CurrentUser.CreateSubKey('Software\OpenConnect-GUI Team\OpenConnect-GUI')
 $existing=$base.OpenSubKey($key)
 if($null -ne $existing){
  try{
   if($existing.GetValue('tolf-device-id') -ne $values.'tolf-device-id' -or $existing.GetValue('server') -ne $values.server -or $existing.GetValue('tolf-cert-sha256') -ne $values.'tolf-cert-sha256'){throw 'A different profile uses this name. Nothing was changed.'}
  }finally{$existing.Close()}
  Write-Host ('Profile already configured: '+$backup.name)
 }else{
  $target=$base.CreateSubKey($key);$created=$true
  foreach($prop in $values.PSObject.Properties){
   if($prop.Name -eq 'server'){continue}
   $kind=[Microsoft.Win32.RegistryValueKind][Enum]::Parse([Microsoft.Win32.RegistryValueKind],[string]$backup.kinds.($prop.Name))
   $value=$prop.Value
   if($kind -eq [Microsoft.Win32.RegistryValueKind]::DWord){$value=[int]$value}
   $target.SetValue($prop.Name,$value,$kind)
  }
  $target.SetValue('server',[string]$values.server,[Microsoft.Win32.RegistryValueKind]::String)
  $target.Flush();$target.Close();$target=$null
  $base.Flush()
  Write-Host ('OK: restored '+$backup.name)
 }
 $created=$false
 if(Test-Path -LiteralPath $backup.exe){Start-Process -FilePath $backup.exe}
 Write-Host 'Select the profile in OpenConnect GUI and click Connect.'
}catch{
 if($target){$target.Close();$target=$null}
 if($created -and $base){$base.DeleteSubKeyTree($key,$false)}
 throw
}finally{
 if($target){$target.Close()};if($base){$base.Close()}
 if($null -ne $plain){[Array]::Clear($plain,0,$plain.Length)}
 $backup=$null;$values=$null
}
'@
    $body=$template.Replace('__SNAPSHOT__',$ProtectedSnapshot)
    $header=@('@echo off','setlocal DisableDelayedExpansion','set "TOLF_RESTORE_FILE=%~f0"',
      'powershell.exe -NoLogo -NoProfile -Command "$s=[IO.File]::ReadAllText($env:TOLF_RESTORE_FILE); & ([scriptblock]::Create(($s -split '':TOLF_RESTORE_PAYLOAD\r?\n'',2)[1]))"',
      'if errorlevel 1 echo Restore failed. Read the error above.','pause','exit /b',':TOLF_RESTORE_PAYLOAD')
    return [string]::Join(([string][char]13+[char]10),$header)+[char]13+[char]10+$body
}

function Save-TolfRemovalCommand {
    try {
        $desktop=[Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
        if(!$desktop){throw 'Desktop folder not found.'}
        $file=Join-Path $desktop ('TOLF VPN Remove - '+([string]$config.name).Substring(5)+'.cmd')
        $content=New-TolfRemovalCommand ([string]$config.name) ([string]$config.deviceId) ([string]$config.gateway)
        [IO.File]::WriteAllText($file,$content,[Text.Encoding]::ASCII)
        Write-Host ('Removal file saved on Desktop: TOLF VPN Remove - '+([string]$config.name).Substring(5)+'.cmd')
        $source=$base.OpenSubKey($profileKey)
        $snapshotBytes=$null
        try {
            $values=@{};$kinds=@{}
            foreach($valueName in $source.GetValueNames()){
                $kind=$source.GetValueKind($valueName)
                if($kind -notin @([Microsoft.Win32.RegistryValueKind]::String,[Microsoft.Win32.RegistryValueKind]::DWord)){throw 'Unsupported profile value type.'}
                $values[$valueName]=$source.GetValue($valueName)
                $kinds[$valueName]=[string]$kind
            }
            $snapshot=@{name=[string]$config.name;exe=$exe;values=$values;kinds=$kinds;files=@($routeFiles)} | ConvertTo-Json -Depth 5 -Compress
            $snapshotBytes=[Text.Encoding]::UTF8.GetBytes($snapshot)
            $sealed=[Security.Cryptography.ProtectedData]::Protect($snapshotBytes,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
            $setupContent=New-TolfRestoreCommand ([Convert]::ToBase64String($sealed))
        }finally{
            $source.Close()
            if($null -ne $snapshotBytes){[Array]::Clear($snapshotBytes,0,$snapshotBytes.Length)}
            $snapshot=$null;$values=$null
        }
        $setupFile=Join-Path $desktop ('TOLF VPN Restore - '+([string]$config.name).Substring(5)+'.cmd')
        [IO.File]::WriteAllText($setupFile,$setupContent,[Text.Encoding]::ASCII)
        Write-Host ('Restore file saved on Desktop: TOLF VPN Restore - '+([string]$config.name).Substring(5)+'.cmd')

    } catch { Write-Warning ('VPN profile is configured, but the Desktop setup/removal files could not be saved: '+$_.Exception.Message) }
}

$routeFiles=@();$routeScript=''
$excluded=@()
if($config.PSObject.Properties['excludedNetworks']){$excluded=@(ConvertTo-TolfExcludedNetworks $config.excludedNetworks)}
if($excluded.Count){
    $routeFiles=@(New-TolfRouteFiles $excluded ([string]$config.deviceId) $exe)
    $routeScript=[string]$routeFiles[1].path
}
$base = $null; $target = $null
$p12 = $null; $keyDer = $null; $keyBytes = $null; $protected = $null; $created = $false; $previous = $null
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
        $existing=$base.OpenSubKey($profileKey)
        try {
            $same=$existing.GetValue('tolf-device-id') -eq [string]$config.deviceId -and $existing.GetValue('server') -eq [string]$config.gateway
            if(!$same){
                Write-Host ('Replace existing local profile: '+[string]$config.name)
                if((Read-Host 'Type REPLACE to confirm') -cne 'REPLACE'){throw 'Cancelled. Existing profile was not changed.'}
            }
            $previous=@{}
            foreach($n in $existing.GetValueNames()){$previous[$n]=@($existing.GetValue($n),$existing.GetValueKind($n))}
        }finally{$existing.Close()}
    }
    $target = $base.CreateSubKey($profileKey); $created = $true
    $stringValues = @{
        'protocol-name'='anyconnect'; 'username'=''; 'interface-name'=''; 'vpnc-script'=$routeScript;
        'tolf-device-id'=[string]$config.deviceId; 'tolf-cert-sha256'=$certHash;
        'ca-cert'='@ByteArray()'; 'server-hash'='@ByteArray()'; 'token-str'='@ByteArray()';
        'client-cert'=('@ByteArray('+$certPem+')');
        'client-key'=('@ByteArray(xxxx'+[Convert]::ToBase64String($protected)+')')
    }
    foreach ($name in $stringValues.Keys) { $target.SetValue($name,$stringValues[$name],[Microsoft.Win32.RegistryValueKind]::String) }
    $numberValues = @{'batch'=0;'proxy'=0;'disable-udp'=0;'minimize-on-connect'=0;'reconnect-timeout'=300;'dtls_attempt_period'=25;'server-hash-algo'=0;'token-type'=-1}
    foreach ($name in $numberValues.Keys) { $target.SetValue($name,[int]$numberValues[$name],[Microsoft.Win32.RegistryValueKind]::DWord) }
    foreach($file in $routeFiles){
        $null=[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName([string]$file.path))
        [IO.File]::WriteAllText([string]$file.path,[string]$file.content,[Text.Encoding]::Unicode)
    }
    # The /server value makes the profile visible. Write it only when complete.
    $target.SetValue('server',[string]$config.gateway,[Microsoft.Win32.RegistryValueKind]::String)
    $target.Flush(); $target.Close(); $target = $null
    $created=$false
    Write-Host ('OK: profile configured: '+[string]$config.name)
    Save-TolfRemovalCommand
    try { Start-Process -FilePath $exe }
    catch { Write-Host 'Open OpenConnect GUI from its shortcut.' }
    Write-Host 'Select the new profile in Server and click Connect.'
} catch {
    if ($target) { $target.Close(); $target = $null }
    if ($created -and $base) {
        $base.DeleteSubKeyTree($profileKey,$false)
        if($null -ne $previous){
            $restore=$base.CreateSubKey($profileKey)
            try{foreach($n in $previous.Keys){$restore.SetValue($n,$previous[$n][0],$previous[$n][1])};$restore.Flush()}finally{$restore.Close()}
        }
    }
    throw
} finally {
    if ($target) { $target.Close() }; if ($base) { $base.Close() }
    if ($rsa) { $rsa.Dispose() }; if ($cert) { $cert.Dispose() }; if ($client) { $client.Dispose() }
    foreach ($bytes in @($p12,$keyDer,$keyBytes,$protected)) {
        if ($null -ne $bytes) { [Array]::Clear($bytes,0,$bytes.Length) }
    }
    $keyPem = $null; $config = $null; $ConfigBase64 = $null
}
