$ErrorActionPreference='Stop'
$s=Get-Content (Join-Path $PSScriptRoot '../../windows/openconnect-setup-v1.ps1') -Raw
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($s,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
$function=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'New-TolfRemovalCommand'},$true)
. ([scriptblock]::Create($function.Extent.Text))
$cmd=New-TolfRemovalCommand 'TOLF Moscow Auto' 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' 'https://oc.tolf.is:4443'
if($cmd -notmatch '-EncodedCommand ([A-Za-z0-9+/=]+)'){throw 'Missing encoded payload'}
$body=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($Matches[1]))
[void][Management.Automation.Language.Parser]::ParseInput($body,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
foreach($expected in @('TOLF Moscow Auto','tolf-device-id','https://oc.tolf.is:4443','Type REMOVE to confirm','-cne','DeleteSubKeyTree($key,$false)','GetSubKeyNames() -contains $key')){
 if(!$body.Contains($expected)){throw "Missing removal guard: $expected"}
}
if($body.Contains('certificateUrl') -or $body.Contains('password') -or $body.Contains('client-key')){throw 'Unexpected credential in removal file'}
if($cmd.ToCharArray() | Where-Object {[int]$_ -gt 127}){throw 'Non-ASCII CMD'}
if($cmd.Length -gt 8000){throw 'CMD line too long'}
'PASS: removal CMD payload, syntax, confirmation and identity guards'
