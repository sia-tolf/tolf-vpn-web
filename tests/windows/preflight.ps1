$ErrorActionPreference = 'Stop'
$script = Get-Content (Join-Path $PSScriptRoot '../../setup/windows/desktop/Preflight.ps1') -Raw
# Real PowerShell parsing, module loading and Add-Type; simulated OS/service failures.
foreach ($case in @('ok','old-os','disabled-service','missing-module')) {
    $prefix = @'
function Get-CimInstance {
 param($ClassName,$Filter)
 if ($ClassName -eq 'Win32_OperatingSystem') {
  [pscustomobject]@{Version=OS_VERSION;ProductType=1}
 } else { [pscustomobject]@{StartMode=SERVICE_MODE} }
}
function Get-VpnConnection { }
'@
    $prefix = $prefix.Replace('OS_VERSION', $(if ($case -eq 'old-os') {"'6.1'"} else {"'10.0'"}))
    $prefix = $prefix.Replace('SERVICE_MODE', $(if ($case -eq 'disabled-service') {"'Disabled'"} else {"'Manual'"}))
    if ($case -eq 'missing-module') {
        $prefix += "`nfunction Import-Module { throw 'Unavailable module' }`n"
    }
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($prefix + "`n" + $script))
    $result = & powershell.exe -NoProfile -NonInteractive -EncodedCommand $encoded
    $code = $LASTEXITCODE
    $expected = switch ($case) {
        'ok' {'TOLF_PREFLIGHT_OK'}
        'old-os' {'TOLF_ERROR:WINDOWS_VERSION'}
        'disabled-service' {'TOLF_ERROR:VPN_SERVICE'}
        'missing-module' {'TOLF_ERROR:VPN_MODULE'}
    }
    if (($result -join "`n") -notmatch $expected) { throw "$case unexpected output: $result" }
    if (($case -eq 'ok' -and $code -ne 0) -or ($case -ne 'ok' -and $code -eq 0)) { throw "$case unexpected exit: $code" }
    Write-Output "PASS $case"
}
# The last child intentionally fails; do not propagate that expected exit to CI.
exit 0
