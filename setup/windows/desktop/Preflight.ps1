$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
function Fail([string]$Code) { Write-Output "TOLF_ERROR:$Code"; exit 1 }
try {
    if ($PSVersionTable.PSVersion -lt [version]'5.1') { Fail 'POWERSHELL_VERSION' }
    if ($ExecutionContext.SessionState.LanguageMode -ne 'FullLanguage') { Fail 'POLICY' }
    $os = Get-CimInstance Win32_OperatingSystem
    if ([version]$os.Version -lt [version]'10.0' -or $os.ProductType -ne 1) { Fail 'WINDOWS_VERSION' }
    try { Import-Module VpnClient -ErrorAction Stop } catch { Fail 'VPN_MODULE' }
    foreach ($name in @('Get-VpnConnection','Add-VpnConnection','Set-VpnConnection','Remove-VpnConnection','Set-VpnConnectionIPsecConfiguration')) {
        if (-not (Get-Command $name -Module VpnClient -ErrorAction SilentlyContinue)) { Fail 'VPN_MODULE' }
    }
    foreach ($name in @('RasMan','IKEEXT','PolicyAgent')) {
        $service = Get-CimInstance Win32_Service -Filter "Name='$name'"
        if (-not $service -or $service.StartMode -eq 'Disabled') { Fail 'VPN_SERVICE' }
    }
    # Exercise the same read access and dynamic compilation used by Configure.ps1.
    Get-VpnConnection -ErrorAction Stop | Out-Null
    Add-Type -TypeDefinition 'public static class TolfPreflight { public static int Check() { return 1; } }' -ErrorAction Stop
    if ([TolfPreflight]::Check() -ne 1) { Fail 'POLICY' }
    Write-Output 'TOLF_PREFLIGHT_OK'
} catch {
    if ($_.FullyQualifiedErrorId -match 'Modules_ModuleNotFound|CommandNotFound') { Fail 'VPN_MODULE' }
    Fail 'PREFLIGHT_ACCESS'
}
