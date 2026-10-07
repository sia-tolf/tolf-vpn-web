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
            if ($store.Name -eq 'Microsoft-Desktop-Provisioning.dat') {
                $base = "$hive\ConnectivityProfiles\VPN\VPNSetting\VPNConfig\VPNSettings"
                foreach ($name in @('AuthenticationTransformConstants','CipherTransformConstants','PfsGroup','DHGroup','IntegrityCheckMethod','EncryptionMethod')) {
                    & reg.exe copy "$base\Server" "$base\$name" /s /f | Add-Content $report
                    if ($LASTEXITCODE -ne 0) { throw "Cannot extend crypto schema: $name" }
                    & reg.exe add "$base\$name" /v Name /t REG_SZ /d $name /f | Add-Content $report
                    if ($LASTEXITCODE -ne 0) { throw "Cannot name crypto setting: $name" }
                    $path = "./Vendor/MSFT/VPNv2/~VPNProfileName~/NativeProfile/CryptographySuite/$name"
                    & reg.exe add "$base\$name\Apply\Csp" /v Path /t REG_SZ /d $path /f | Add-Content $report
                    if ($LASTEXITCODE -ne 0) { throw "Cannot set native crypto URI: $name" }
                }
                & reg.exe query $base /s | Add-Content $report
            }
            foreach ($term in @('CryptographySuite')) {
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
    & $icd.FullName /Build-ProvisioningPackage "/CustomizationXML:$destination/customizations.xml" "/PackagePath:$destination/TOLF-PPKG-Test.ppkg" "/StoreFile:$($store.FullName)" "/CommonLogFolder:$destination" +Overwrite 2>&1 | Tee-Object -FilePath "$destination/compiler-output.txt"
    $code = $LASTEXITCODE
    "Compiler exit code: $code" | Add-Content $report
    if ($code -ne 0) { throw "ICD build failed: $code" }
    $package = Get-Item "$destination/TOLF-PPKG-Test.ppkg"
    if ($package.Length -lt 100) { throw 'Compiled PPKG missing or empty' }
    $extracted = Join-Path $env:RUNNER_TEMP 'tolf-ppkg-extracted'
    New-Item $extracted -ItemType Directory -Force | Out-Null
    & dism.exe /English /Apply-Image "/ImageFile:$($package.FullName)" /Index:1 "/ApplyDir:$extracted" 2>&1 | Add-Content $report
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect compiled PPKG payload' }
    & python "$PSScriptRoot/verify-package.py" "$extracted" | Tee-Object -FilePath "$destination/payload-verification.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Compiled PPKG payload verification failed' }
    Get-FileHash $package.FullName -Algorithm SHA256 | Format-List | Out-File "$destination/SHA256SUMS.txt"
} catch {
    $_.Exception.Message | Add-Content $report
    throw
}
