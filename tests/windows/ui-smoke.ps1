$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class NativeUi {
 public delegate bool EnumProc(IntPtr w,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr w,EnumProc cb,IntPtr p);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr w,out uint id);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr w,StringBuilder s,int n);
 public static void Dump(int pid) { EnumWindows((w,p)=>{uint id;GetWindowThreadProcessId(w,out id);if(id==pid){var s=new StringBuilder(1024);GetWindowText(w,s,1024);Console.WriteLine("Window: "+s);EnumChildWindows(w,(c,q)=>{var t=new StringBuilder(1024);GetWindowText(c,t,1024);Console.WriteLine("Child: "+t);return true;},IntPtr.Zero);}return true;},IntPtr.Zero); }

 [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left,Top,Right,Bottom; }
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string cls,string title);
 [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr w,int id);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr w);
 [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr w);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr w,out Rect r);
 [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr w,uint msg,IntPtr a,IntPtr b);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr w,IntPtr dc,uint flags);
}
'@
$exe = (Resolve-Path './setup/windows/dist/TOLF-Setup.exe').Path
$process = $null
$profileName = $null
try {
 $process = Start-Process $exe -ArgumentList '--manage' -PassThru
 Write-Output ((Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine)
 $window = [IntPtr]::Zero
 for ($i=0; $i -lt 150; $i++) {
  Start-Sleep -Milliseconds 200
  $window = [NativeUi]::FindWindow('TolfVpnController','TOLF VPN 2.6.1')
  if ($window -ne [IntPtr]::Zero -and [NativeUi]::GetDlgItem($window,205) -ne [IntPtr]::Zero) { break }
 }
 if ($window -eq [IntPtr]::Zero -or $process.HasExited) { [NativeUi]::Dump($process.Id); $process.Refresh(); Write-Output "Exited=$($process.HasExited) ExitCode=$($process.ExitCode)"; throw 'Controller did not start' }
 Start-Sleep -Milliseconds 500
 if (-not [NativeUi]::IsWindowVisible([NativeUi]::GetDlgItem($window,202))) { throw 'Settings field is not visible' }
 if ([NativeUi]::IsWindowEnabled([NativeUi]::GetDlgItem($window,204))) { throw 'Empty profile list must not allow dialing' }
 function Save-Window([string]$name) {
  $rect = New-Object NativeUi+Rect
  [void][NativeUi]::GetWindowRect($window,[ref]$rect)
  $bitmap = New-Object System.Drawing.Bitmap(($rect.Right-$rect.Left),($rect.Bottom-$rect.Top))
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $dc = $graphics.GetHdc()
  try { [void][NativeUi]::PrintWindow($window,$dc,2) } finally { $graphics.ReleaseHdc($dc) }
  $bitmap.Save((Join-Path (Resolve-Path './setup/windows/dist').Path $name),[System.Drawing.Imaging.ImageFormat]::Png)
  $graphics.Dispose(); $bitmap.Dispose()
 }
 $profileName = 'TOLF - Riga - ' + [guid]::NewGuid().ToString()
 [xml]$eap = '<EapHostConfig xmlns="http://www.microsoft.com/provisioning/EapHostConfig"><EapMethod><Type xmlns="http://www.microsoft.com/provisioning/EapCommon">26</Type><VendorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorId><VendorType xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorType><AuthorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</AuthorId></EapMethod><Config xmlns="http://www.microsoft.com/provisioning/EapHostConfig"><Eap xmlns="http://www.microsoft.com/provisioning/BaseEapConnectionPropertiesV1"><Type>26</Type><EapType xmlns="http://www.microsoft.com/provisioning/MsChapV2ConnectionPropertiesV1"><UseWinLogonCredentials>false</UseWinLogonCredentials></EapType></Eap></Config></EapHostConfig>'
 Add-VpnConnection -Name $profileName -ServerAddress 'ikev2-riga.tolf.is' -TunnelType Ikev2 -AuthenticationMethod Eap -EncryptionLevel Required -RememberCredential -EapConfigXmlStream $eap -Force | Out-Null
 $labelKey = 'HKCU:\Software\TOLF\VPN\' + $profileName.Substring(14)
 New-Item -Path $labelKey -Force | Out-Null
 New-ItemProperty -Path $labelKey -Name DisplayName -Value 'Test Windows' -PropertyType String -Force | Out-Null
 New-ItemProperty -Path $labelKey -Name RoutingMode -Value 'sr' -PropertyType String -Force | Out-Null
 [void][NativeUi]::SendMessage($window,0x8016,[IntPtr]::Zero,[IntPtr]::Zero)
 Start-Sleep -Milliseconds 500
 if (-not [NativeUi]::IsWindowEnabled([NativeUi]::GetDlgItem($window,204))) { throw 'Installed TOLF profile was not discovered' }
 if ([NativeUi]::IsWindowVisible([NativeUi]::GetDlgItem($window,203))) { throw 'Save should be hidden until settings change' }
 [void][NativeUi]::SendMessage($window,0x111,[IntPtr]208,[IntPtr]::Zero)
 [void][NativeUi]::SendMessage($window,0x111,[IntPtr]208,[IntPtr]::Zero)
 $caption = New-Object System.Text.StringBuilder 512
 [void][NativeUi]::GetWindowText([NativeUi]::GetDlgItem($window,210),$caption,512)
 if ($caption.ToString() -notmatch 'Test Windows.*Riga.*SR') { throw "Wrong friendly profile label: $caption" }
 Save-Window 'settings-preview.png' 
 [void][NativeUi]::SendMessage($window,0x111,[IntPtr]211,[IntPtr]::Zero)
 if (-not [NativeUi]::IsWindowVisible([NativeUi]::GetDlgItem($window,212))) { throw 'Password field did not open' }
 if ([NativeUi]::IsWindowEnabled([NativeUi]::GetDlgItem($window,204))) { throw 'Do not dial while editing password' }
 Save-Window 'password-preview.png'
 [void][NativeUi]::SendMessage($window,0x111,[IntPtr]214,[IntPtr]::Zero)
 if ([NativeUi]::IsWindowVisible([NativeUi]::GetDlgItem($window,212))) { throw 'Password field did not close' }
 [void][NativeUi]::SendMessage($window,0x111,[IntPtr]205,[IntPtr]::Zero)
 if ([NativeUi]::IsWindowVisible([NativeUi]::GetDlgItem($window,202))) { throw 'Widget still exposes settings fields' }
 if (-not [NativeUi]::IsWindowVisible([NativeUi]::GetDlgItem($window,204))) { throw 'Widget connection button is hidden' }
 Start-Sleep -Milliseconds 500
 Save-Window 'widget-preview.png'
 Write-Output 'PASS native settings startup, empty-profile guard and compact widget layout'
} finally {
 if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
 if ($labelKey) { Remove-Item -Path $labelKey -Recurse -Force -ErrorAction SilentlyContinue }
 if ($profileName) { Remove-VpnConnection -Name $profileName -Force -ErrorAction SilentlyContinue }
}

