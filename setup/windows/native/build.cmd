@echo off
setlocal
cd /d "%~dp0.."
if not exist dist mkdir dist
rc /nologo /fo dist\version.res native\version.rc
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W4 /MT /O2 /Fo:dist\main.obj /Fe:dist\TOLF-Setup.exe native\main.cpp dist\version.res /link /SUBSYSTEM:WINDOWS /MANIFEST:EMBED /MANIFESTINPUT:native\app.manifest user32.lib gdi32.lib ole32.lib oleaut32.lib wbemuuid.lib winhttp.lib rasapi32.lib rasdlg.lib shell32.lib advapi32.lib
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /utf-8 /EHsc /W4 /MT /O2 /Fo:dist\tests.obj /Fe:dist\native-tests.exe ..\..\tests\windows\native.cpp /link ole32.lib oleaut32.lib wbemuuid.lib winhttp.lib rasapi32.lib rasdlg.lib shell32.lib advapi32.lib
if errorlevel 1 exit /b 1
dumpbin /dependents dist\TOLF-Setup.exe > dist\dependencies.txt
if errorlevel 1 exit /b 1
exit /b 0
