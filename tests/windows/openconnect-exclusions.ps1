$ErrorActionPreference='Stop'
$s=Get-Content (Join-Path $PSScriptRoot '../../windows/openconnect-setup-v1.ps1') -Raw
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($s,[ref]$tokens,[ref]$errors)
foreach($name in @('ConvertTo-TolfExcludedNetworks','New-TolfRouteFiles')){
 $fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
 . ([scriptblock]::Create($fn.Extent.Text))
}
if((@(ConvertTo-TolfExcludedNetworks @('192.168.200.118/24','10.0.21.10/32')) -join ',') -ne '192.168.200.0/24,10.0.21.10/32'){throw 'Normalization failed'}
foreach($bad in @('0.0.0.0/0','256.0.0.1/24','10.1.2.3/33','10.1.2.3/24;calc')){
 $rejected=$false;try{ConvertTo-TolfExcludedNetworks @($bad)}catch{$rejected=$true}
 if(!$rejected){throw 'Invalid network accepted'}
}
$env:LOCALAPPDATA='/tmp/tolf-routing-test'
function Test-Path {param($LiteralPath) if($LiteralPath -like '*vpnc-script.js'){return $true};return $null -ne $script:stateJson}
$script:stateJson=$null
$files=@(New-TolfRouteFiles @('192.168.200.0/24','10.0.21.10/32') 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' '/opt/OpenConnect/openconnect-gui.exe')
$hook=$files[0].content;$wrapper=$files[1].content
[void][Management.Automation.Language.Parser]::ParseInput($hook,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
if(!$wrapper.Contains('cscript.exe') -or !$wrapper.Contains('reason == "connect"')){throw 'Wrapper missing'}
$script:routes=@([pscustomobject]@{DestinationPrefix='192.168.200.0/24';InterfaceIndex=10;NextHop='0.0.0.0';RouteMetric=256})
$script:gateway='192.168.200.1'
function Find-NetRoute {param($RemoteIPAddress,$ErrorAction)
 $hop=if($RemoteIPAddress -eq '192.168.200.0'){'0.0.0.0'}else{$script:gateway}
 [pscustomobject]@{DestinationPrefix='0.0.0.0/0';InterfaceIndex=10;NextHop=$hop}
}
function Get-NetRoute {param($AddressFamily,$DestinationPrefix,$InterfaceIndex,$PolicyStore,$ErrorAction)
 @($script:routes | Where-Object {$_.DestinationPrefix -eq $DestinationPrefix -and $_.InterfaceIndex -eq $InterfaceIndex})
}
function New-NetRoute {param($DestinationPrefix,$InterfaceIndex,$NextHop,$RouteMetric,$PolicyStore,$ErrorAction)
 if($script:failAdd){throw 'Simulated add failure'}
 $script:routes+= [pscustomobject]@{DestinationPrefix=$DestinationPrefix;InterfaceIndex=$InterfaceIndex;NextHop=$NextHop;RouteMetric=$RouteMetric}
}
function Remove-NetRoute {param([Parameter(ValueFromPipeline=$true)]$InputObject,$Confirm)
 process{$script:routes=@($script:routes | Where-Object {$_ -ne $InputObject})}
}
function Set-Content {param($LiteralPath,$Encoding,[Parameter(ValueFromPipeline=$true)]$Value) process{$script:stateJson=$Value}}
function Get-Content {param($LiteralPath,[switch]$Raw) $script:stateJson}
function Remove-Item {param($LiteralPath,[switch]$Force) $script:stateJson=$null}
$script:failAdd=$false
$env:reason='connect';$env:TUNIDX='99'
& ([scriptblock]::Create($hook))
if($script:routes.Count -ne 2){throw 'Excluded host route not created'}
if(($script:stateJson | ConvertFrom-Json).Count -ne 1){throw 'Preexisting route incorrectly claimed'}
$env:reason='disconnect';& ([scriptblock]::Create($hook))
if($script:routes.Count -ne 1 -or $script:routes[0].RouteMetric -ne 256){throw 'Preexisting route removed'}
$script:gateway='192.168.200.254'
$env:reason='connect';& ([scriptblock]::Create($hook))
if($script:routes[1].NextHop -ne $script:gateway){throw 'Gateway was not refreshed'}
$env:reason='disconnect';& ([scriptblock]::Create($hook))
$script:failAdd=$true;$env:reason='connect';$failed=$false
try{& ([scriptblock]::Create($hook))}catch{$failed=$true}
if(!$failed -or $script:routes.Count -ne 1){throw 'Failure cleanup failed'}
'PASS: exclusions validation, existing route preservation, connect/disconnect, gateway refresh and failure cleanup'

[IO.File]::WriteAllText((Join-Path ([IO.Path]::GetTempPath()) 'tolf-test-route-wrapper.js'),$wrapper)
