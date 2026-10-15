(()=>{
const OC_SETUP_SHA256='a627509e39b5f135152315b331778211f6a03095599c22d90b7e85ae031cbdb2';

function parseExclusions(input){
 const entries=Array.isArray(input)?input:String(input||"").split(/[\s,;]+/);
 const result=[];
 for(const raw of entries){
  const value=String(raw).trim();if(!value)continue;
  const m=value.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?:\/(\d{1,2}))?$/);
  if(!m||m.slice(1,5).some(n=>Number(n)>255))throw Error("Invalid IPv4 address or network: "+value);
  const prefix=m[5]===undefined?32:Number(m[5]);
  if(prefix<1||prefix>32)throw Error("Use an IPv4 prefix from /1 to /32: "+value);
  const ip=m.slice(1,5).reduce((n,b)=>(n*256+Number(b))>>>0,0);
  const mask=(0xffffffff<<(32-prefix))>>>0,network=(ip&mask)>>>0;
  const normalized=[network>>>24,(network>>>16)&255,(network>>>8)&255,network&255].join(".")+"/"+prefix;
  if(!result.includes(normalized))result.push(normalized);
 }
 if(result.length>32)throw Error("Maximum 32 excluded networks");
 return result;
}

function windowsSetupCommand(grant,point,mode="auto",exclusions=[]){
 const cities={moscow:"Moscow",riga:"Riga",us:"New York"},modes={auto:"Auto",ru:"RU",lv:"LV",us:"US",yt:"YT"};
 if(!cities[point.id]||!modes[mode]||({moscow:"oc.tolf.is:4443",riga:"oc-riga.tolf.is:443",us:"oc-us.tolf.is:4443"}[point.id])!==point.host)throw Error("Invalid Windows setup selection");
 const cert=new URL(grant.certificateUrl);
 if(!/^[a-f0-9-]{36}$/.test(grant.deviceId)||grant.username!=="tolf-oc-"+grant.deviceId.replaceAll("-","")||cert.origin!=="https://api.tolf.is"||cert.search||cert.hash||cert.username||cert.password||!/^\/oc\/access\/import\/[A-Za-z0-9_-]{43}\.p12$/.test(cert.pathname))throw Error("Invalid Windows certificate grant");
 const config={excludedNetworks:parseExclusions(exclusions),deviceId:grant.deviceId,username:grant.username,certificateUrl:grant.certificateUrl,password:grant.password,
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

window.TolfWindowsSetup={command:windowsSetupCommand,file:windowsCommandFile,parseExclusions};
})();
