param([Parameter(Mandatory=$true)][string]$InputDirectory,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable CI runner only.' }
New-Item $OutputDirectory -ItemType Directory -Force | Out-Null
Import-Module VpnClient
Import-Module Provisioning
$report=[ordered]@{OS=(Get-CimInstance Win32_OperatingSystem).Caption;Cases=[ordered]@{};ConnectionTested=$false}
$names=@('TOLF-CI-EAP-1','TOLF-CI-EAP-2','TOLF-CI-PPKG')
function Check-Eap([xml]$actual,[xml]$expected) {
    $paths=@('Type','SimpleCertSelection','DisableUserPromptForServerValidation','ServerNames','TrustedRootCA','DifferentUsername','PerformServerValidation','AcceptServerName','AllPurposeEnabled','IssuerHash','EKUOID')
    foreach ($field in $paths) {
        $a=@($actual.SelectNodes("//*[local-name()='$field']") | ForEach-Object {$_.InnerText})
        $e=@($expected.SelectNodes("//*[local-name()='$field']") | ForEach-Object {$_.InnerText})
        if ($field -in @('TrustedRootCA','IssuerHash')) {
            $a=@($a | ForEach-Object {($_ -replace '\s','').ToUpperInvariant()})
            $e=@($e | ForEach-Object {($_ -replace '\s','').ToUpperInvariant()})
        }
        if (($a -join '|') -ne ($e -join '|') -or $a.Count -eq 0) { throw "EAP readback mismatch: $field actual=$($a -join '|') expected=$($e -join '|')" }
    }
    foreach ($field in @('CAHashList','ClientAuthEKUList','AnyPurposeEKUList')) {
        $a=$actual.SelectSingleNode("//*[local-name()='$field']")
        $e=$expected.SelectSingleNode("//*[local-name()='$field']")
        if (!$a -or $a.GetAttribute('Enabled') -ne $e.GetAttribute('Enabled')) {throw "Filter readback mismatch: $field"}
    }
    if ($actual.SelectSingleNode("//*[local-name()='UseWinLogonCredentials']")) {throw 'Password EAP method appeared.'}
}
try {
    foreach ($index in @(1,2)) {
        $name='TOLF-CI-EAP-'+$index
        [xml]$xml=Get-Content (Join-Path $InputDirectory ("Eap-"+$index+".xml")) -Raw
        Add-VpnConnection -Name $name -ServerAddress 'vpn-ci.invalid' -TunnelType Ikev2 -AuthenticationMethod Eap -EapConfigXmlStream $xml -SplitTunneling -AllUserConnection -Force | Out-Null
        $vpn=Get-VpnConnection -Name $name -AllUserConnection
        $vpn.EapConfigXmlStream.OuterXml | Set-Content (Join-Path $OutputDirectory ($name+'.xml'))
        Write-Output $vpn.EapConfigXmlStream.OuterXml
        Check-Eap $vpn.EapConfigXmlStream $xml
        $report.Cases[$name]=@{Passed=$true;Authentication=[string]$vpn.AuthenticationMethod}
        $vpn.EapConfigXmlStream.OuterXml | Set-Content (Join-Path $OutputDirectory ($name+'.xml'))
    }
    Install-ProvisioningPackage -PackagePath (Join-Path $InputDirectory 'TOLF-CI-Crypto.ppkg') -QuietInstall -ForceInstall -LogsDirectoryPath $OutputDirectory | Format-List * | Out-File (Join-Path $OutputDirectory 'installation.txt')
    $vpn=Get-VpnConnection -Name 'TOLF-CI-PPKG' -AllUserConnection
    [xml]$expected=Get-Content (Join-Path $InputDirectory 'Eap-1.xml') -Raw
    if ([string]$vpn.AuthenticationMethod -ne 'Eap') {throw 'PPKG authentication is not EAP.'}
    Check-Eap $vpn.EapConfigXmlStream $expected
    $suite=@{AuthenticationTransformConstants='SHA256128';CipherTransformConstants='AES256';DHGroup='Group14';EncryptionMethod='AES256';IntegrityCheckMethod='SHA256';PfsGroup='PFS2048'}
    foreach ($field in $suite.Keys) {if ([string]$vpn.IPsecCustomPolicy.$field -ne $suite[$field]) {throw "PPKG crypto mismatch: $field"}}
    $report.Cases['TOLF-CI-PPKG']=@{Passed=$true;Authentication=[string]$vpn.AuthenticationMethod;Crypto=$suite}
    $vpn.EapConfigXmlStream.OuterXml | Set-Content (Join-Path $OutputDirectory 'PPKG-EAP.xml')
} catch {
    $report.Error=$_.Exception.Message
    throw
} finally {
    $report | ConvertTo-Json -Depth 7 | Tee-Object -FilePath (Join-Path $OutputDirectory 'result.json')
    foreach ($name in $names) {Remove-VpnConnection -Name $name -AllUserConnection -Force -ErrorAction SilentlyContinue}
}
