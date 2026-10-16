// Manual confirmation of Cisco installation on this browser/device platform.
(() => {
 const host=document.getElementById('ciscoClientInstall');
 if(!host)return;
 const remembered=new Set();
 let strongSwanConfirmed=false;
 try{strongSwanConfirmed=sessionStorage.getItem('tolfStrongSwanInstalled')==='true';}catch{}
 const needsStrongSwan=()=>platform()==='android'&&transport()==='ikev2';
 const needsApp=()=>transport()==='anyconnect'||needsStrongSwan();
 const appConfirmed=()=>needsStrongSwan()?strongSwanConfirmed:window.isCiscoClientConfirmed(platform());
 const confirmationKey=p=>'tolfCiscoInstalled:'+p;
 for(const p of ['ios','android','windows']){
  try{if(sessionStorage.getItem(confirmationKey(p))==='true')remembered.add(p);}catch{}
 }
 const texts={
  ru:{title:'1. Установите Cisco Secure Client (AnyConnect).',install:'Установить Cisco Secure Client',confirmed:'Cisco Secure Client установлен',blocked:'Чтобы продолжить, подтвердите установку Cisco Secure Client в разделе «Мой VPN».',back:'К подтверждению установки'},
  en:{title:'1. Install Cisco Secure Client (AnyConnect).',install:'Install Cisco Secure Client',confirmed:'Cisco Secure Client is installed',blocked:'Confirm Cisco Secure Client installation in My VPN to continue.',back:'Confirm installation'},
  lv:{title:'1. Instalējiet Cisco Secure Client (AnyConnect).',install:'Instalēt Cisco Secure Client',confirmed:'Cisco Secure Client ir instalēts',blocked:'Lai turpinātu, sadaļā Mans VPN apstipriniet Cisco Secure Client instalēšanu.',back:'Apstiprināt instalēšanu'}
 };
 const copy=()=>{
  const c={...(texts[document.documentElement.lang]||texts.en)};
  if(needsStrongSwan())for(const key of ['title','install','confirmed','blocked'])c[key]=c[key].replaceAll('Cisco Secure Client','strongSwan VPN Client').replace(' (AnyConnect)',' (IKEv2)');
  if(platform()==='windows')for(const key of ['title','install','confirmed','blocked'])c[key]=c[key].replaceAll('Cisco Secure Client','OpenConnect GUI');
  const store=platform()==='ios'?'App Store':platform()==='android'?'Google Play':null;
  if(store){
   const language=document.documentElement.lang;
   const suffix=language==='ru'?' из '+store:language==='lv'?' no '+store:' from '+store;
   c.install+=suffix;
   c.title=c.title.replace(/\.$/,'')+suffix+'.';
  }
  return c;
 };
 const platform=()=>typeof currentPlatform!=='undefined'?currentPlatform:'ios';
 const transport=()=>window.getVpnTransport?.()||'';
 window.isCiscoClientConfirmed=p=>{
  p=p||platform();if(!['ios','android','windows'].includes(p))return false;
  return remembered.has(p);
 };
 window.getCiscoInstallCopy=copy;
 window.focusCiscoInstall=()=>{
  host.classList.remove('hidden');
  host.scrollIntoView?.({behavior:'smooth',block:'center'});
  host.querySelector?.('input')?.focus?.();
 };
 function render(){
  const c=copy(),p=platform();host.classList.toggle('hidden',!needsApp());
  host.dataset.confirmed=String(appConfirmed());
  host.replaceChildren();
  const title=document.createElement('h3');title.textContent=c.title;
  const app=document.createElement('a');app.className='button-link secondary';
  app.textContent=c.install;app.target='_blank';app.rel='noopener noreferrer';
  app.href=needsStrongSwan()?'https://play.google.com/store/apps/details?id=org.strongswan.android':p==='ios'?'https://apps.apple.com/app/id1135064690':p==='android'?'https://play.google.com/store/apps/details?id=com.cisco.anyconnect.vpn.android.avf':'https://www.infradead.org/openconnect-gui/download/openconnect-gui-1.6.2-win64.exe';
  const label=document.createElement('label');label.className='cisco-install-confirm';
  const check=document.createElement('input');check.type='checkbox';check.checked=appConfirmed();
  check.addEventListener('change',()=>{
   if(needsStrongSwan()){
    strongSwanConfirmed=check.checked;
    try{sessionStorage.setItem('tolfStrongSwanInstalled',String(check.checked));}catch{}
    render();return;
   }
   if(check.checked)remembered.add(p);else remembered.delete(p);
   try{if(check.checked)sessionStorage.setItem(confirmationKey(p),'true');else sessionStorage.removeItem(confirmationKey(p));}catch{}
   window.dispatchEvent(new Event('tolf:cisco-install-confirmed'));render();
  });
  const text=document.createElement('span');text.textContent=c.confirmed;
  label.append(check,text);host.append(title,app,label);
  const blocked=!transport()||(needsApp()&&!appConfirmed());
  if(blocked&&needsApp()){const note=document.createElement('p');note.className='card-description';note.textContent=c.blocked;host.append(note);}
  for(const id of ['quickSetupLink','manualSetupLink'])document.getElementById(id)?.setAttribute('aria-disabled',String(blocked));
 }
 for(const id of ['quickSetupLink','manualSetupLink']){
  document.getElementById(id)?.addEventListener('click',event=>{
   if(!transport()){
    event.preventDefault();event.stopImmediatePropagation();document.querySelector('#vpnProtocolDropdown button')?.focus();return;
   }
   if(needsApp()&&!appConfirmed()){
    event.preventDefault();event.stopImmediatePropagation();window.focusCiscoInstall();
   }
  },true);
 }
 for(const event of ['vpntransportchange','vpnplatformchange'])window.addEventListener(event,render);
 window.addEventListener('pageshow',render);
 new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 render();
})();
