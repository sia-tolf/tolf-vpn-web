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
        $deadline = (Get-Date).AddMinutes(7)
        while (!(Test-Path $resultPath) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 2 }
        if (!(Test-Path $resultPath) -and (Test-Path (Join-Path $OutputDirectory 'checkpoint.json'))) { Get-Content (Join-Path $OutputDirectory 'checkpoint.json') -Raw }
        if (Test-Path (Join-Path $OutputDirectory 'progress.txt')) { Get-Content (Join-Path $OutputDirectory 'progress.txt') }
        if (!(Test-Path $resultPath)) { throw 'SYSTEM crypto test timed out.' }
        $json = Get-Content $resultPath -Raw
        Write-Output $json
        Get-ChildItem $OutputDirectory -Filter '*.txt' | ForEach-Object {
            Write-Output ('DIAGNOSTIC: ' + $_.Name)
            Get-Content $_.FullName
        }
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
    $xml = Get-Content (Join-Path $InputDirectory 'ProfileXML.xml') -Raw
    $minimal = '<VPNProfile><NativeProfile><Servers>vpn-ci.invalid</Servers><NativeProtocolType>IKEv2</NativeProtocolType><Authentication><MachineMethod>Certificate</MachineMethod></Authentication></NativeProfile></VPNProfile>'
    $cases = @(
        @{Key='CSP'; Name='TOLF-CI-CSP'; Xml=$xml; Encoded=$true},
        @{Key='CSPMinimal'; Name='TOLF-CI-CSP-MIN'; Xml=$minimal; Encoded=$true}
    )
    [xml]$fullDocument = $xml
    $cryptoNode = $fullDocument.VPNProfile.NativeProfile.CryptographySuite
    $fullNoCrypto = $fullDocument.Clone()
    $null = $fullNoCrypto.VPNProfile.NativeProfile.RemoveChild($fullNoCrypto.VPNProfile.NativeProfile.CryptographySuite)
    $cases += @{Key='FullNoCrypto'; Name='TOLF-CI-NOCRYPTO'; Xml=$fullNoCrypto.OuterXml; Encoded=$true}
    [xml]$minimalCrypto = $minimal
    $null = $minimalCrypto.VPNProfile.NativeProfile.InsertBefore($minimalCrypto.ImportNode($cryptoNode,$true), $minimalCrypto.VPNProfile.NativeProfile.Authentication)
    $cases += @{Key='MinimalCrypto'; Name='TOLF-CI-CRYPTO'; Xml=$minimalCrypto.OuterXml; Encoded=$true}
    foreach ($child in $cryptoNode.ChildNodes) {
        [xml]$single = $minimal
        $suite = $single.CreateElement('CryptographySuite')
        $null = $suite.AppendChild($single.ImportNode($child,$true))
        $null = $single.VPNProfile.NativeProfile.InsertBefore($suite,$single.VPNProfile.NativeProfile.Authentication)
        $cases += @{Key=('Only'+$child.Name); Name=('TOLF-CI-ONLY-'+$child.Name); Xml=$single.OuterXml; Encoded=$true}
    }
    foreach ($option in @('RememberCredentials','AlwaysOn','RoutingPolicyType','DisableClassBasedDefaultRoute')) {
        [xml]$single = $minimal
        $source = $fullDocument.SelectSingleNode('//' + $option)
        if ($source.ParentNode.Name -eq 'VPNProfile') {
            $null = $single.VPNProfile.InsertBefore($single.ImportNode($source,$true),$single.VPNProfile.NativeProfile)
        } elseif ($option -eq 'RoutingPolicyType') {
            $null = $single.VPNProfile.NativeProfile.InsertBefore($single.ImportNode($source,$true),$single.SelectSingleNode('/VPNProfile/NativeProfile/NativeProtocolType'))
        } else {
            $null = $single.VPNProfile.NativeProfile.InsertBefore($single.ImportNode($source,$true),$single.VPNProfile.NativeProfile.Authentication)
        }
        $cases += @{Key=('Only'+$option); Name=('TOLF-CI-ONLY-'+$option); Xml=$single.OuterXml; Encoded=$true}
    }
    # Test every combination of optional settings with the proven crypto block.
    $options = @('RememberCredentials','AlwaysOn','RoutingPolicyType','DisableClassBasedDefaultRoute')
    for ($mask=1; $mask -lt 16; $mask++) {
        [xml]$combo = $xml
        $combo.SelectSingleNode('/VPNProfile/NativeProfile/Servers').InnerText = 'vpn-ci.invalid'
        for ($i=0; $i -lt $options.Count; $i++) {
            if (($mask -band (1 -shl $i)) -eq 0) {
                $node = $combo.SelectSingleNode('//' + $options[$i])
                $null = $node.ParentNode.RemoveChild($node)
            }
        }
        $cases += @{Key=('Options'+$mask); Name=('TOLF-CI-OPTIONS-'+$mask); Xml=$combo.OuterXml; Encoded=$true}
    }
    [xml]$realHost = $minimalCrypto.OuterXml
    $realHost.SelectSingleNode('/VPNProfile/NativeProfile/Servers').InnerText = $fullDocument.SelectSingleNode('/VPNProfile/NativeProfile/Servers').InnerText
    $cases += @{Key='MinimalCryptoRealHost'; Name='TOLF-CI-REALHOST'; Xml=$realHost.OuterXml; Encoded=$true}
    if ($env:TOLF_CI_SWEEP -ne 'true') {
        $cases = @($cases | Where-Object { $_.Key -in @('CSP','CSPMinimal','MinimalCrypto') })
    }
    foreach ($case in $cases) {
        ('START ' + $case.Key + ' ' + (Get-Date).ToString('o')) | Add-Content (Join-Path $OutputDirectory 'progress.txt')
        try {
            $class = Get-CimClass -Namespace $namespace -ClassName 'MDM_VPNv2_01'
            $report.CspClass = $class.CimClassName
            $inputXml = $case.Xml
            if ($case.Encoded) { $inputXml = [System.Security.SecurityElement]::Escape($inputXml) }
            $created = New-CimInstance -Namespace $namespace -ClassName 'MDM_VPNv2_01' -Property @{
                ParentID='./Vendor/MSFT/VPNv2'; InstanceID=$case.Name; ProfileXML=$inputXml
            }
            $report.Results[$case.Key] = Read-Policy $case.Name
            $report.Results[$case.Key].ProfileXML = $created.ProfileXML
            $report.Results[$case.Key].Created = $true
        } catch {
            $report.Results[$case.Key] = @{
                Error=$_.Exception.Message; HResult=$_.Exception.HResult
                Details=($_ | Format-List * -Force | Out-String)
                Matches=$false
            }
        }
        ('END ' + $case.Key + ' ' + (Get-Date).ToString('o')) | Add-Content (Join-Path $OutputDirectory 'progress.txt')
        ('SERIALIZE ' + (Get-Date).ToString('o')) | Add-Content (Join-Path $OutputDirectory 'progress.txt')
        $checkpoint = [ordered]@{Results=$report.Results; Expected=$expected}
        $checkpointJson = ConvertTo-Json -InputObject $checkpoint -Depth 6
        [System.IO.File]::WriteAllText((Join-Path $OutputDirectory 'checkpoint.json'),$checkpointJson)
        ('SAVED ' + (Get-Date).ToString('o')) | Add-Content (Join-Path $OutputDirectory 'progress.txt')
    }
    $packageCases = @(
        @{Key='PPKG'; Name='TOLF-CI-PPKG'; File='TOLF-CI-Crypto.ppkg'},
        @{Key='PPKGMinimalSingle'; Name='TOLF-CI-PPKG-MIN-1'; File='TOLF-CI-PPKG-MIN-1.ppkg'},
        @{Key='PPKGMinimalDouble'; Name='TOLF-CI-PPKG-MIN-2'; File='TOLF-CI-PPKG-MIN-2.ppkg'}
    )
    foreach ($packageCase in $packageCases) {
        ('START ' + $packageCase.Key + ' ' + (Get-Date).ToString('o')) | Add-Content (Join-Path $OutputDirectory 'progress.txt')
        try {
            Import-Module Provisioning
            $package = Join-Path $InputDirectory $packageCase.File
            $install = Install-ProvisioningPackage -PackagePath $package -QuietInstall -ForceInstall -LogsDirectoryPath $OutputDirectory
            $install | Format-List * -Force | Out-File (Join-Path $OutputDirectory ($packageCase.Key + '-provisioning-result.txt'))
            $report.Results[$packageCase.Key] = Read-Policy $packageCase.Name
        } catch { $report.Results[$packageCase.Key] = @{Error=$_.Exception.Message;Matches=$false} }
        ('END ' + $packageCase.Key + ' ' + (Get-Date).ToString('o')) | Add-Content (Join-Path $OutputDirectory 'progress.txt')
        ('SERIALIZE ' + (Get-Date).ToString('o')) | Add-Content (Join-Path $OutputDirectory 'progress.txt')
        $checkpoint = [ordered]@{Results=$report.Results; Expected=$expected}
        $checkpointJson = ConvertTo-Json -InputObject $checkpoint -Depth 6
        [System.IO.File]::WriteAllText((Join-Path $OutputDirectory 'checkpoint.json'),$checkpointJson)
        ('SAVED ' + (Get-Date).ToString('o')) | Add-Content (Join-Path $OutputDirectory 'progress.txt')
    }
    foreach ($archive in Get-ChildItem $OutputDirectory -Filter 'Logs.*.zip') {
        $expanded = Join-Path $OutputDirectory $archive.BaseName
        Expand-Archive -LiteralPath $archive.FullName -DestinationPath $expanded -Force
        foreach ($etl in Get-ChildItem $expanded -Filter '*.etl' -Recurse) {
            Get-WinEvent -Path $etl.FullName -Oldest -ErrorAction SilentlyContinue |
                Where-Object { $_.Level -le 3 -or $_.Message -match 'TOLF|VPNv2|ProfileXML|error|failed' } |
                Select-Object -First 40 TimeCreated,Id,LevelDisplayName,Message |
                Format-List | Out-File (Join-Path $OutputDirectory ($archive.BaseName + '-' + $etl.BaseName + '.txt'))
        }
    }
    $report.Events = @()
    foreach ($log in @('Microsoft-Windows-Provisioning-Diagnostics-Provider/Admin', 'Microsoft-Windows-DeviceManagement-Enterprise-Diagnostics-Provider/Admin')) {
        $report.Events += @(Get-WinEvent -FilterHashtable @{LogName=$log; StartTime=$started} -ErrorAction SilentlyContinue | Select-Object -First 20 TimeCreated,Id,Message)
    }
    $report.Passed = $report.Results.Baseline.Matches -and $report.Results.CSP.Matches -and $report.Results.PPKG.Matches
} catch {
    $report.Fatal = $_.Exception.Message
} finally {
    # Only names created by this disposable-runner test are removed.
    try {
        Get-CimInstance -Namespace $namespace -ClassName 'MDM_VPNv2_01' -ErrorAction Stop |
            Where-Object { $_.InstanceID -in @($cases.Name) + @($packageCases.Name) } |
            Remove-CimInstance -ErrorAction Stop
    } catch { $report.CleanupCsp = $_.Exception.Message }
    foreach ($name in @('TOLF-CI-BASE') + @($cases.Name) + @($packageCases.Name)) {
        Remove-VpnConnection -AllUserConnection -Name $name -Force -ErrorAction SilentlyContinue
    }
    $report | ConvertTo-Json -Depth 12 | Set-Content ($resultPath + '.tmp') -Encoding UTF8
    Move-Item ($resultPath + '.tmp') $resultPath -Force
}
if (!$report.Passed) { exit 1 }
