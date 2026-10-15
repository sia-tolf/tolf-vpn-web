(()=>{
const OC_SETUP_SHA256='155a120190aaaaf1b06eabada1a0614e3b8975b9f291dc56e60c2b487f8264e7';
function windowsSetupCommand(grant,point,mode="auto"){
 const cities={moscow:"Moscow",riga:"Riga",us:"New York"},modes={auto:"Auto",ru:"RU",lv:"LV",us:"US",yt:"YT"};
 if(!cities[point.id]||!modes[mode]||({moscow:"oc.tolf.is:4443",riga:"oc-riga.tolf.is:443",us:"oc-us.tolf.is:4443"}[point.id])!==point.host)throw Error("Invalid Windows setup selection");
 const cert=new URL(grant.certificateUrl);
 if(!/^[a-f0-9-]{36}$/.test(grant.deviceId)||grant.username!=="tolf-oc-"+grant.deviceId.replaceAll("-","")||cert.origin!=="https://api.tolf.is"||cert.search||cert.hash||cert.username||cert.password||!/^\/oc\/access\/import\/[A-Za-z0-9_-]{43}\.p12$/.test(cert.pathname))throw Error("Invalid Windows certificate grant");
 const config={deviceId:grant.deviceId,username:grant.username,certificateUrl:grant.certificateUrl,password:grant.password,
  gateway:'https://'+point.host,name:'TOLF '+cities[point.id]+' '+modes[mode]};
 const bytes=new TextEncoder().encode(JSON.stringify(config));
 const encoded=btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));
 return "$ErrorActionPreference='Stop'; if ($PSVersionTable.PSVersion -lt [version]'5.1') { throw 'Windows PowerShell 5.1 or newer is required. Install Windows updates before running setup again.' } $win = Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion'; if ([int]$win.CurrentBuildNumber -lt 10240) { throw 'This Windows version is too old for automatic setup. Use an updated Windows 10 or Windows 11 computer.' } $net = Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\NET Framework Setup\\NDP\\v4\\Full' -ErrorAction SilentlyContinue; if ($null -eq $net -or [int]$net.Release -lt 461808) { throw '.NET Framework 4.7.2 or newer is required. Install .NET Framework 4.8 from https://dotnet.microsoft.com/download/dotnet-framework/net48 and run setup again.' }; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $ocBytes=(New-Object Net.WebClient).DownloadData('https://vpn.tolf.is/windows/openconnect-setup-v1.ps1?v="+OC_SETUP_SHA256+"'); $ocHash=[BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($ocBytes)).Replace('-','').ToLowerInvariant(); if($ocHash -ne '"+OC_SETUP_SHA256+"'){throw 'Setup script verification failed'}; & ([scriptblock]::Create([Text.Encoding]::UTF8.GetString($ocBytes))) -ConfigBase64 '"+encoded+"'";
}
function windowsCommandFile(command){
 // All dynamic values are base64. CMD must receive one quoted, ASCII command.
 if(/[^\x20-\x7e]|["%!]/.test(command)||command.length>7000)throw Error('Invalid Windows command');
 return '@echo off\r\nsetlocal DisableDelayedExpansion\r\nwhere powershell.exe >nul 2>&1\r\nif errorlevel 1 (\r\n  echo Windows PowerShell is missing. Enable Windows PowerShell 5.1 or update Windows.\r\n  pause\r\n  exit /b 1\r\n)\r\npowershell.exe -NoLogo -NoProfile -Command "'+command+'"\r\nif errorlevel 1 (\r\n  echo Setup failed. Read the error above.\r\n  pause\r\n  exit /b 1\r\n)\r\necho Setup complete. Select your profile in OpenConnect GUI and click Connect.\r\npause\r\nexit /b 0\r\n';
}

window.TolfWindowsSetup={command:windowsSetupCommand,file:windowsCommandFile};
})();
