# TOLF: per-user Windows 10/11 native IKEv2 connection.
# Does not connect automatically or change machine-wide security settings.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module VpnClient
$config = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'connection.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($config.server -ne 'ikev2-riga.tolf.is' -or $config.deviceId -notmatch '^[0-9a-f-]{36}$') {
    throw 'Invalid TOLF configuration'
}
$name = 'TOLF - Riga - ' + $config.deviceId
[xml]$eap = @'
<EapHostConfig xmlns="http://www.microsoft.com/provisioning/EapHostConfig">
 <EapMethod><Type xmlns="http://www.microsoft.com/provisioning/EapCommon">26</Type><VendorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorId><VendorType xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorType><AuthorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</AuthorId></EapMethod>
 <Config xmlns="http://www.microsoft.com/provisioning/EapHostConfig"><Eap xmlns="http://www.microsoft.com/provisioning/BaseEapConnectionPropertiesV1"><Type>26</Type><EapType xmlns="http://www.microsoft.com/provisioning/MsChapV2ConnectionPropertiesV1"><UseWinLogonCredentials>false</UseWinLogonCredentials></EapType></Eap></Config>
</EapHostConfig>
'@
$existing = Get-VpnConnection -ErrorAction Stop | Where-Object Name -eq $name
if ($existing -and ($existing.ServerAddress -ne $config.server -or $existing.TunnelType -ne 'Ikev2')) {
    throw 'A different VPN connection already uses this name. Nothing changed.'
}
if ($existing -and $existing.ConnectionStatus -eq 'Connected') {
    throw 'Disconnect this TOLF connection before updating its configuration.'
}
$created = $false
try {
    if (-not $existing) {
        Add-VpnConnection -Name $name -ServerAddress $config.server -TunnelType Ikev2 -AuthenticationMethod Eap -EapConfigXmlStream $eap -EncryptionLevel Required -SplitTunneling $false -RememberCredential -Force | Out-Null
        $created = $true
    } else {
        Set-VpnConnection -Name $name -ServerAddress $config.server -TunnelType Ikev2 -AuthenticationMethod Eap -EapConfigXmlStream $eap -EncryptionLevel Required -SplitTunneling $false -RememberCredential $true -Force | Out-Null
    }
    Set-VpnConnectionIPsecConfiguration -ConnectionName $name -AuthenticationTransformConstants SHA256128 -CipherTransformConstants AES256 -EncryptionMethod AES256 -IntegrityCheckMethod SHA256 -DHGroup Group14 -PfsGroup None -Force | Out-Null
    if (-not ('Tolf.Ras' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace Tolf {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode, Pack=4)]
 public struct Credentials {
  public UInt32 Size;
  public UInt32 Mask;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=257)] public string User;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=257)] public string Password;
  [MarshalAs(UnmanagedType.ByValTStr, SizeConst=16)] public string Domain;
 }
 public static class Ras {
  [DllImport("rasapi32.dll", CharSet=CharSet.Unicode, ExactSpelling=true)]
  public static extern UInt32 RasSetCredentialsW(string phonebook, string entry, ref Credentials credentials, [MarshalAs(UnmanagedType.Bool)] bool clear);
 }
}
'@
    }
    $cred = New-Object Tolf.Credentials
    $cred.Size = [Runtime.InteropServices.Marshal]::SizeOf($cred)
    $cred.Mask = 7
    $cred.User = $config.username
    $cred.Password = $config.password
    $cred.Domain = ''
    $phonebook = Join-Path $env:APPDATA 'Microsoft\Network\Connections\Pbk\rasphone.pbk'
    $result = [Tolf.Ras]::RasSetCredentialsW($phonebook, $name, [ref]$cred, $false)
    $cred.Password = ''
    $config.password = ''
    if ($result -ne 0) { throw "Windows could not save VPN credentials (RAS error $result)." }
    Write-Host 'TOLF VPN is configured. Open Settings > Network & Internet > VPN to connect.'
    Write-Host 'After successful setup, delete the downloaded ZIP and its extracted folder: they contain the VPN password.'
    Start-Process 'ms-settings:network-vpn'
} catch {
    if ($created) { Remove-VpnConnection -Name $name -Force -ErrorAction SilentlyContinue }
    throw
}
