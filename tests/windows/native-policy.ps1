# Build-time cross-check against the inbox provider's published numeric enums.
# The installed native EXE neither reads CDXML nor launches PowerShell.
$ErrorActionPreference = 'Stop'
$file = Get-ChildItem "$env:WINDIR/System32/WindowsPowerShell/v1.0/Modules/VpnClient/*IPsec*.cdxml" | Select-Object -First 1
[xml]$doc = Get-Content $file.FullName
$expected = @{
 AuthenticationTransformConstants = @('SHA256128',2)
 CipherTransformConstants = @('AES256',5)
 EncryptionMethod = @('AES256',4)
 IntegrityCheckMethod = @('SHA256',2)
 DHGroup = @('Group14',3)
 PfsGroup = @('None',0)
}
foreach ($key in $expected.Keys) {
 $enum = $doc.PowerShellMetadata.Enums.Enum | Where-Object EnumName -eq "VpnConnectionIPsecConfiguration.$key"
 $item = $enum.Value | Where-Object Name -eq $expected[$key][0]
 if (-not $item -or [uint32]$item.Value -ne $expected[$key][1]) { throw "Native IPsec constant mismatch: $key" }
}
Write-Output 'PASS native IPsec constants match Windows provider schema'
