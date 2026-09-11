$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$out = Join-Path $root 'dist'
New-Item -ItemType Directory -Force $out | Out-Null
$tokens=$null; $parseErrors=$null
[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'desktop/Configure.ps1'),[ref]$tokens,[ref]$parseErrors) | Out-Null
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$csc = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
& $csc /nologo /target:winexe /platform:anycpu /optimize+ /reference:System.dll /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll "/resource:$root/desktop/Configure.ps1,Configure.ps1" "/out:$out/TOLF-Setup.exe" "$root/desktop/TolfSetup.cs"
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
Get-FileHash "$out/TOLF-Setup.exe" -Algorithm SHA256
