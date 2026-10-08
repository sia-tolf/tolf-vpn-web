param(
    [Parameter(Mandatory=$true)][string]$InputDirectory,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [switch]$Worker
)
$ErrorActionPreference = 'Stop'
if (-not $Worker -and $env:GITHUB_ACTIONS -ne 'true') { throw 'This test runs only on a disposable GitHub Actions VM.' }
New-Item $OutputDirectory -ItemType Directory -Force | Out-Null
$resultPath = Join-Path $OutputDirectory 'result.json'
if (-not $Worker) {
    $task = 'TOLF-CI-Crypto-' + [guid]::NewGuid().ToString('N')
    $arguments = '-NoProfile -NonInteractive -File "' + $PSCommandPath + '" -InputDirectory "' + $InputDirectory + '" -OutputDirectory "' + $OutputDirectory + '" -Worker'
    $action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument $arguments
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    try {
        Register-ScheduledTask -TaskName $task -Action $action -Principal $principal | Out-Null
        Start-ScheduledTask -TaskName $task
        $deadline = (Get-Date).AddMinutes(3)
        while (!(Test-Path $resultPath) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 2 }
        if (!(Test-Path $resultPath)) { throw 'SYSTEM crypto test timed out.' }
        $json = Get-Content $resultPath -Raw
        Write-Output $json
        if (!(ConvertFrom-Json $json).Passed) { throw 'Windows crypto readback comparison failed; inspect result.json.' }
    } finally {
        if ((Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue).State -eq 'Running') { Stop-ScheduledTask -TaskName $task }
        Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction SilentlyContinue
    }
    exit
}
$expected = [ordered]@{
    AuthenticationTransformConstants='SHA256128'; CipherTransformConstants='AES256'
    EncryptionMethod='AES256'; IntegrityCheckMethod='SHA256'; DHGroup='Group14'; PfsGroup='None'
}
$report = [ordered]@{
    OS = (Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture)
    Identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    Expected = $expected
    Results = [ordered]@{}
    Passed = $false
}
function Read-Policy([string]$name) {
    $vpn = Get-VpnConnection -AllUserConnection -Name $name -ErrorAction Stop
    $actual = [ordered]@{}
    foreach ($key in $expected.Keys) { $actual[$key] = [string]$vpn.IPsecCustomPolicy.$key }
    $matches = $true
    foreach ($key in $expected.Keys) { if ($actual[$key] -ne $expected[$key]) { $matches = $false } }
    return [ordered]@{Name=$name;Actual=$actual;Matches=$matches;Authentication=[string]$vpn.AuthenticationMethod}
}
$namespace = 'root\cimv2\mdm\dmmap'
$started = Get-Date
try {
    if ($report.Identity -ne 'NT AUTHORITY\SYSTEM') { throw 'Expected SYSTEM context.' }
    Import-Module VpnClient
    try {
        Add-VpnConnection -Name 'TOLF-CI-BASE' -ServerAddress 'vpn-ci.invalid' -TunnelType Ikev2 -AuthenticationMethod MachineCertificate -AllUserConnection -Force | Out-Null
        Set-VpnConnectionIPsecConfiguration -ConnectionName 'TOLF-CI-BASE' -AllUserConnection -AuthenticationTransformConstants SHA256128 -CipherTransformConstants AES256 -EncryptionMethod AES256 -IntegrityCheckMethod SHA256 -DHGroup Group14 -PfsGroup None -Force | Out-Null
        $report.Results.Baseline = Read-Policy 'TOLF-CI-BASE'
    } catch { $report.Results.Baseline = @{Error=$_.Exception.Message;Matches=$false} }
    try {
        $class = Get-CimClass -Namespace $namespace -ClassName 'MDM_VPNv2_01'
        $report.CspClass = $class.CimClassName
        $xml = Get-Content (Join-Path $InputDirectory 'ProfileXML.xml') -Raw
        # WMI bridge expects HTML-escaped ProfileXML, as in Microsoft's sample.
        $encoded = [System.Security.SecurityElement]::Escape($xml)
        $created = New-CimInstance -Namespace $namespace -ClassName 'MDM_VPNv2_01' -Property @{
            ParentID='./Vendor/MSFT/VPNv2'; InstanceID='TOLF-CI-CSP'; ProfileXML=$encoded
        }
        $report.Results.CSP = Read-Policy 'TOLF-CI-CSP'
        $report.CspProfileXML = (Get-CimInstance -Namespace $namespace -ClassName 'MDM_VPNv2_01' | Where-Object InstanceID -eq 'TOLF-CI-CSP').ProfileXML
    } catch { $report.Results.CSP = @{Error=$_.Exception.Message;Matches=$false} }
    try {
        Import-Module Provisioning
        $package = Join-Path $InputDirectory 'TOLF-CI-Crypto.ppkg'
        Install-ProvisioningPackage -PackagePath $package -QuietInstall -ForceInstall -LogsDirectoryPath $OutputDirectory | Out-File (Join-Path $OutputDirectory 'provisioning-result.txt')
        $report.Results.PPKG = Read-Policy 'TOLF-CI-PPKG'
    } catch { $report.Results.PPKG = @{Error=$_.Exception.Message;Matches=$false} }
    $report.Events = @(Get-WinEvent -FilterHashtable @{
        LogName='Microsoft-Windows-Provisioning-Diagnostics-Provider/Admin'; StartTime=$started
    } -ErrorAction SilentlyContinue | Where-Object Message -match 'TOLF-CI-' | Select-Object -First 10 TimeCreated,Id,Message)
    $report.Passed = $report.Results.Baseline.Matches -and $report.Results.CSP.Matches -and $report.Results.PPKG.Matches
} catch {
    $report.Fatal = $_.Exception.Message
} finally {
    # Only names created by this disposable-runner test are removed.
    try {
        Get-CimInstance -Namespace $namespace -ClassName 'MDM_VPNv2_01' -ErrorAction Stop |
            Where-Object { $_.InstanceID -in @('TOLF-CI-CSP','TOLF-CI-PPKG') } |
            Remove-CimInstance -ErrorAction Stop
    } catch { $report.CleanupCsp = $_.Exception.Message }
    foreach ($name in @('TOLF-CI-BASE','TOLF-CI-CSP','TOLF-CI-PPKG')) {
        Remove-VpnConnection -AllUserConnection -Name $name -Force -ErrorAction SilentlyContinue
    }
    $report | ConvertTo-Json -Depth 12 | Set-Content ($resultPath + '.tmp') -Encoding UTF8
    Move-Item ($resultPath + '.tmp') $resultPath -Force
}
if (!$report.Passed) { exit 1 }
