$ErrorActionPreference = 'Stop'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC build tools required on build machine' }
$dev = Join-Path $vs 'Common7/Tools/VsDevCmd.bat'
$build = Join-Path $PSScriptRoot 'native/build.cmd'
& cmd.exe /d /s /c "`"`"$dev`" -arch=x64 -host_arch=x64 && `"$build`"`""
if ($LASTEXITCODE -ne 0) { throw 'Native installer compilation failed' }
$deps = Get-Content (Join-Path $PSScriptRoot 'dist/dependencies.txt') -Raw
Write-Output $deps
if ($deps -match '(?i)mscoree|vcruntime|msvcp|ucrtbase|api-ms-win-crt') { throw 'Unexpected external runtime dependency' }
Get-FileHash (Join-Path $PSScriptRoot 'dist/TOLF-Setup.exe') -Algorithm SHA256
