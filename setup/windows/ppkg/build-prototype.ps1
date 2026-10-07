$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot 'dist'
New-Item $destination -ItemType Directory -Force | Out-Null
$report = Join-Path $destination 'compiler-report.txt'
$root = "${env:ProgramFiles(x86)}\Windows Kits\10\Assessment and Deployment Kit\Imaging and Configuration Designer"
try {
    $icd = Get-ChildItem $root -Recurse -Filter ICD.exe | Select-Object -First 1
    if (-not $icd) { throw 'Microsoft ICD.exe not found' }
    "Compiler: $($icd.VersionInfo.FileVersion)" | Set-Content $report
    $stores = @(Get-ChildItem $root -Recurse -Filter '*.dat')
    foreach ($store in $stores) {
        "Store: $($store.Name)" | Add-Content $report
        try {
            [xml]$schema = Get-Content $store.FullName -Raw
            foreach ($node in $schema.SelectNodes('//*')) {
                if ($node.Attributes -and (($node.Attributes | ForEach-Object { $_.Value }) -join ' ') -match 'VPN|CryptographySuite|EapUserData|UserContext') {
                    $ancestors = @(); $parent = $node
                    while ($parent -and $parent.NodeType -eq 'Element') {
                        $ancestors = @("$($parent.Name)[$(($parent.Attributes | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ',')]") + $ancestors
                        $parent = $parent.ParentNode
                    }
                    ($ancestors -join '/') | Add-Content $report
                }
            }
        } catch { "Schema read: $($_.Exception.Message.Substring(0,[Math]::Min(300,$_.Exception.Message.Length)))" | Add-Content $report }
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
