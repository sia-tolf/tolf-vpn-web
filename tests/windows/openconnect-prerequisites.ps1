$ErrorActionPreference='Stop'
$s=Get-Content (Join-Path $PSScriptRoot '../../windows/openconnect-setup-v1.ps1') -Raw
$start=$s.IndexOf('if ($PSVersionTable.PSVersion')
$end=$s.IndexOf("if (Get-Process -Name 'openconnect-gui'")
$checks=$s.Substring($start,$end-$start).Replace('$PSVersionTable.PSVersion','$testVersion')
function Get-ItemProperty {
 param($Path,$ErrorAction)
 if($Path -like '*CurrentVersion'){return [pscustomobject]@{CurrentBuildNumber=$testBuild}}
 if($testRelease -eq 0){return $null}
 return [pscustomobject]@{Release=$testRelease}
}
foreach($case in @(
 @('5.1',10240,461808,''),
 @('5.1',26100,533320,''),
 @('4.0',26100,533320,'PowerShell 5.1'),
 @('5.1',9600,533320,'Windows version is too old'),
 @('5.1',26100,461807,'.NET Framework 4.7.2'),
 @('5.1',26100,0,'.NET Framework 4.7.2')
)){
 $testVersion=[version]$case[0];$testBuild=$case[1];$testRelease=$case[2]
 $actual=''
 try{& ([scriptblock]::Create($checks))}catch{$actual=$_.Exception.Message}
 if($case[3] -eq ''){if($actual){throw $actual}}
 elseif(!$actual.Contains($case[3])){throw "Wrong prerequisite result: $actual"}
}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseInput($s,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
'PASS: Windows setup syntax and six prerequisite cases'
