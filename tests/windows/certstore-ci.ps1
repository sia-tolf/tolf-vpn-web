param([Parameter(Mandatory=$true)][string]$InputDirectory,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true') {throw 'Disposable CI runner only.'}
New-Item $OutputDirectory -ItemType Directory -Force | Out-Null
$meta=Get-Content (Join-Path $InputDirectory 'certscope-metadata.json') -Raw | ConvertFrom-Json
$report=[ordered]@{Identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name;Scopes=[ordered]@{};ConnectionTested=$false}
$allThumbs=@($meta.Scopes.Device.Certificates.Thumbprint)+@($meta.Scopes.User.Certificates.Thumbprint)
try {
    foreach ($scope in @('Device','User')) {
        $logs=Join-Path $OutputDirectory $scope
        New-Item $logs -ItemType Directory -Force | Out-Null
        try {
            Install-ProvisioningPackage -PackagePath (Join-Path $InputDirectory ("TOLF-CI-CERT-"+$scope+".ppkg")) -QuietInstall -ForceInstall -LogsDirectoryPath $logs |
                Format-List * | Out-File (Join-Path $logs 'installation.txt')
        } catch {$report.Scopes[$scope]=@{InstallError=$_.Exception.Message}}
        $items=@()
        foreach ($expected in $meta.Scopes.$scope.Certificates) {
            $user=Get-Item ("Cert:\CurrentUser\My\"+$expected.Thumbprint) -ErrorAction SilentlyContinue
            $machine=Get-Item ("Cert:\LocalMachine\My\"+$expected.Thumbprint) -ErrorAction SilentlyContinue
            $items+=@{Thumbprint=$expected.Thumbprint;UserPresent=[bool]$user;UserPrivateKey=([bool]$user -and $user.HasPrivateKey);MachinePresent=[bool]$machine;MachinePrivateKey=([bool]$machine -and $machine.HasPrivateKey);ExpectedOID=$expected.OID;UserOIDs=@(($user.Extensions | Where-Object {$_.Oid.Value -eq '2.5.29.37'}).EnhancedKeyUsages.Value);MachineOIDs=@(($machine.Extensions | Where-Object {$_.Oid.Value -eq '2.5.29.37'}).EnhancedKeyUsages.Value)}
        }
        $report.Scopes[$scope]=@{Certificates=$items;Installation=$report.Scopes[$scope]}
    }
    foreach ($row in $report.Scopes.Device.Certificates) {if (!$row.MachinePrivateKey -or $row.UserPresent) {throw 'Device control did not install only to LocalMachine/My.'}}
    foreach ($row in $report.Scopes.User.Certificates) {
        if (!$row.UserPrivateKey -or $row.MachinePresent) {throw 'User-scoped PPKG did not install only to CurrentUser/My.'}
        if ($row.UserOIDs -notcontains $row.ExpectedOID) {throw 'User certificate custom EKU lost.'}
    }
    $report.Passed=$true
} catch {
    $report.Passed=$false;$report.Error=$_.Exception.Message
    throw
} finally {
    $report | ConvertTo-Json -Depth 10 | Tee-Object -FilePath (Join-Path $OutputDirectory 'result.json')
    foreach ($thumb in $allThumbs) {
        foreach ($store in @('Cert:\CurrentUser\My\','Cert:\LocalMachine\My\')) {Remove-Item ($store+$thumb) -ErrorAction SilentlyContinue}
    }
    Remove-Item ("Cert:\LocalMachine\Root\"+$meta.CA) -ErrorAction SilentlyContinue
}
