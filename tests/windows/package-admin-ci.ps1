param([Parameter(Mandatory=$true)][string]$InputDirectory,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable CI runner only.' }
$identity=[System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object System.Security.Principal.WindowsPrincipal($identity)
if (!$principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Elevated runner identity required.' }
New-Item $OutputDirectory -ItemType Directory -Force | Out-Null
Import-Module VpnClient
Import-Module Provisioning
$expected=@{AuthenticationTransformConstants='SHA256128';CipherTransformConstants='AES256';EncryptionMethod='AES256';IntegrityCheckMethod='SHA256';DHGroup='Group14';PfsGroup='None'}
$report=[ordered]@{Identity=$identity.Name;Results=[ordered]@{}}
foreach ($level in @(1,2)) {
    $name='TOLF-CI-PPKG-MIN-'+$level
    try {
        $install=Install-ProvisioningPackage -PackagePath (Join-Path $InputDirectory ($name+'.ppkg')) -QuietInstall -ForceInstall -LogsDirectoryPath $OutputDirectory
        $install | Format-List * -Force | Out-File (Join-Path $OutputDirectory ('admin-install-'+$level+'.txt'))
        $vpn=Get-VpnConnection -Name $name -AllUserConnection -ErrorAction Stop
        $actual=[ordered]@{}; $matches=$true
        foreach ($key in $expected.Keys) { $actual[$key]=[string]$vpn.IPsecCustomPolicy.$key; if ($actual[$key] -ne $expected[$key]) {$matches=$false} }
        $report.Results[$name]=@{Actual=$actual;Matches=$matches;Authentication=[string]$vpn.AuthenticationMethod}
    } catch { $report.Results[$name]=@{Error=$_.Exception.Message;Matches=$false} }
}
$report | ConvertTo-Json -Depth 6 | Tee-Object -FilePath (Join-Path $OutputDirectory 'admin-result.json')
Get-ChildItem $OutputDirectory -Filter 'admin-install-*.txt' | ForEach-Object { Get-Content $_.FullName }
foreach ($archive in Get-ChildItem $OutputDirectory -Filter 'Logs.*.zip') {
    $expanded=Join-Path $OutputDirectory $archive.BaseName
    Expand-Archive -LiteralPath $archive.FullName -DestinationPath $expanded -Force
    foreach ($etl in Get-ChildItem $expanded -Filter '*.etl' -Recurse) {
        Get-WinEvent -Path $etl.FullName -Oldest -ErrorAction SilentlyContinue |
            Where-Object { $_.Level -le 3 -or $_.Message -match 'TOLF|VPNv2|ProfileXML|error|failed' } |
            Select-Object -First 40 TimeCreated,Id,LevelDisplayName,Message,@{n='Values';e={@($_.Properties | ForEach-Object {[string]$_.Value})}},@{n='EventXML';e={$_.ToXml()}} |
            Format-List | Out-String | Tee-Object -FilePath (Join-Path $OutputDirectory ($archive.BaseName+'-admin-etl.txt'))
    }
}
