$ErrorActionPreference='Stop'
$s=Get-Content (Join-Path $PSScriptRoot '../../windows/openconnect-setup-v1.ps1') -Raw
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($s,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
$fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'New-TolfRestoreCommand'},$true)
. ([scriptblock]::Create($fn.Extent.Text))
$cmd=New-TolfRestoreCommand 'AQIDBA=='
$body=($cmd -split ':TOLF_RESTORE_PAYLOAD\r?\n',2)[1]
[void][Management.Automation.Language.Parser]::ParseInput($body,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
foreach($expected in @('Unprotect','CurrentUser','openconnect-gui','tolf-device-id','tolf-cert-sha256','Profile already configured','DeleteSubKeyTree($key,$false)')){
 if(!$body.Contains($expected)){throw "Missing restore guard: $expected"}
}
if($body.Contains('DownloadData') -or $body.Contains('certificateUrl')){throw 'Restore must work offline'}
$invalidRejected=$false
try{New-TolfRestoreCommand "bad'input"}catch{$invalidRejected=$true}
if(!$invalidRejected){throw 'Invalid payload accepted'}
# The CMD launcher remains short even with a large encrypted backup.
$large=New-TolfRestoreCommand ('A'*20000)
$line=($large -split '\r?\n' | Where-Object {$_ -like 'powershell.exe*'})
if($line.Length -gt 1000){throw 'Oversize CMD launch line'}
'PASS: offline restore payload, guards, syntax and CMD length'

# Exercise the emitted restore logic with in-memory registry and DPAPI substitutes.
$script:items=@{};$script:deletions=0
$script:profile=[pscustomobject]@{}
$script:profile | Add-Member ScriptMethod GetValue {param($n) $script:items[$n]}
$script:profile | Add-Member ScriptMethod SetValue {param($n,$v,$k) $script:items[$n]=$v}
$script:profile | Add-Member ScriptMethod Flush {}
$script:profile | Add-Member ScriptMethod Close {}
$script:present=$false
$script:testBase=[pscustomobject]@{}
$script:testBase | Add-Member ScriptMethod OpenSubKey {param($n) if($script:present){return $script:profile};return $null}
$script:testBase | Add-Member ScriptMethod CreateSubKey {param($n) $script:present=$true;return $script:profile}
$script:testBase | Add-Member ScriptMethod DeleteSubKeyTree {param($n,$ignored) $script:deletions++;$script:present=$false}
$script:testBase | Add-Member ScriptMethod Flush {}
$script:testBase | Add-Member ScriptMethod Close {}
function Get-Process {param($Name,$ErrorAction) return $null}
function Test-Path {param($LiteralPath) return $false}
$values=@{'server'='https://oc.tolf.is:4443';'tolf-device-id'='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';'tolf-cert-sha256'='testhash';'batch'=0}
$kinds=@{'server'='String';'tolf-device-id'='String';'tolf-cert-sha256'='String';'batch'='DWord'}
$script:testPlain=[Text.Encoding]::UTF8.GetBytes((@{name='TOLF Moscow Auto';exe='unused';values=$values;kinds=$kinds}|ConvertTo-Json -Depth 5))
# Clone because the generated script clears plaintext after each attempt.
$run=$body.Replace("[Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String('AQIDBA=='),"+'$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)', '[byte[]]$script:testPlain.Clone()')
$run=$run.Replace("[Microsoft.Win32.Registry]::CurrentUser.CreateSubKey('Software\OpenConnect-GUI Team\OpenConnect-GUI')",'$script:testBase')
& ([scriptblock]::Create($run))
if(!$script:present -or $script:items.server -ne $values.server -or $script:items.batch -isnot [int]){throw 'Restore failed'}
& ([scriptblock]::Create($run))
if($script:deletions -ne 0){throw 'Existing profile was modified'}
$script:items['tolf-device-id']='different'
$rejected=$false
try{& ([scriptblock]::Create($run))}catch{$rejected=$_.Exception.Message.Contains('different profile')}
if(!$rejected -or $script:deletions -ne 0 -or $script:items['tolf-device-id'] -ne 'different'){throw 'Conflicting profile was not protected'}
'PASS: restore creation, repeated setup and conflicting-profile protection'
