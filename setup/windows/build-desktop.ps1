$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$out = Join-Path $root 'dist'
New-Item -ItemType Directory -Force $out | Out-Null
$tokens=$null; $parseErrors=$null
[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'desktop/Configure.ps1'),[ref]$tokens,[ref]$parseErrors) | Out-Null
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$csc = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$source = Join-Path $root 'desktop\TolfSetup.cs'
$resource = Join-Path $root 'desktop\Configure.ps1'
$preflight = Join-Path $root 'desktop\Preflight.ps1'
[System.Management.Automation.Language.Parser]::ParseFile($preflight,[ref]$tokens,[ref]$parseErrors) | Out-Null
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$binary = Join-Path $out 'TOLF-Setup.exe'
& $csc /nologo /target:winexe /platform:anycpu /optimize+ /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll "/resource:$resource,Configure.ps1" "/resource:$preflight,Preflight.ps1" "/out:$binary" $source
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
Get-FileHash "$out/TOLF-Setup.exe" -Algorithm SHA256
