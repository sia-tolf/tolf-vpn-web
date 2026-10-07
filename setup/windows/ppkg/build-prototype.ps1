$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot 'dist'
New-Item $destination -ItemType Directory -Force | Out-Null
$report = Join-Path $destination 'compiler-report.txt'
$root = "${env:ProgramFiles(x86)}\Windows Kits\10\Assessment and Deployment Kit\Imaging and Configuration Designer"
try {
    $icd = Get-ChildItem $root -Recurse -Filter ICD.exe | Select-Object -First 1
    if (-not $icd) { throw 'Microsoft ICD.exe not found' }
    "Compiler: $($icd.VersionInfo.FileVersion)" | Set-Content $report
    $toolDirectory = Join-Path $env:RUNNER_TEMP 'tolf-icd'
    Copy-Item $icd.Directory.FullName $toolDirectory -Recurse -Force
    $icd = Get-Item (Join-Path $toolDirectory 'ICD.exe')
    $stores = @(Get-ChildItem $toolDirectory -Filter '*.dat')
    foreach ($store in $stores | Where-Object { $_.Name -match 'Common|Desktop' }) {
        "Store: $($store.Name)" | Add-Content $report
        $hive = 'HKLM\TolfPpkgCompilerStore'
        & reg.exe load $hive $store.FullName | Add-Content $report
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect compiler settings store' }
        try {
            foreach ($term in @('VPN', 'CryptographySuite', 'ProfileXML', 'ProvisioningCommands', 'UserContext')) {
                "Schema search: $term" | Add-Content $report
                & reg.exe query $hive /s /f $term 2>&1 | Add-Content $report
            }
        } finally {
            & reg.exe unload $hive | Add-Content $report
            if ($LASTEXITCODE -ne 0) { throw 'Cannot release compiler settings store' }
        }
    }
    & python "$PSScriptRoot/customization.py" --output "$destination/customizations.xml"
    if ($LASTEXITCODE -ne 0) { throw 'Customization generation failed' }
    $store = $stores | Where-Object { $_.Name -eq 'Microsoft-Desktop-Provisioning.dat' } | Select-Object -First 1
    if (-not $store) { throw 'Desktop provisioning store not found' }
    & $icd.FullName /Build-ProvisioningPackage "/CustomizationXML:$destination/customizations.xml" "/PackagePath:$destination/TOLF-PPKG-Test.ppkg" "/StoreFile:$($store.FullName)" +Overwrite 2>&1 | Tee-Object -FilePath "$destination/compiler-output.txt"
    $code = $LASTEXITCODE
    "Compiler exit code: $code" | Add-Content $report
    if ($code -ne 0) { throw "ICD build failed: $code" }
    $package = Get-Item "$destination/TOLF-PPKG-Test.ppkg"
    if ($package.Length -lt 100) { throw 'Compiled PPKG missing or empty' }
    Get-FileHash $package.FullName -Algorithm SHA256 | Format-List | Out-File "$destination/SHA256SUMS.txt"
} catch {
    $_.Exception.Message | Add-Content $report
    throw
}
