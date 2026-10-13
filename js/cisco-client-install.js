// Manual confirmation of Cisco installation on this browser/device platform.
(() => {
 const host=document.getElementById('ciscoClientInstall');
 if(!host)return;
 const remembered=new Set();
 const texts={
  ru:{title:'1. Установите Cisco Secure Client (AnyConnect).',install:'Установить Cisco Secure Client',confirmed:'Cisco Secure Client установлен',blocked:'Чтобы продолжить, подтвердите установку Cisco Secure Client в разделе «Мой VPN».',back:'К подтверждению установки'},
  en:{title:'1. Install Cisco Secure Client (AnyConnect).',install:'Install Cisco Secure Client',confirmed:'Cisco Secure Client is installed',blocked:'Confirm Cisco Secure Client installation in My VPN to continue.',back:'Confirm installation'},
  lv:{title:'1. Instalējiet Cisco Secure Client (AnyConnect).',install:'Instalēt Cisco Secure Client',confirmed:'Cisco Secure Client ir instalēts',blocked:'Lai turpinātu, sadaļā Mans VPN apstipriniet Cisco Secure Client instalēšanu.',back:'Apstiprināt instalēšanu'}
 };
 const copy=()=>{
  const c={...(texts[document.documentElement.lang]||texts.en)};
  if(platform()==='windows')for(const key of ['title','install','confirmed','blocked'])c[key]=c[key].replaceAll('Cisco Secure Client','OpenConnect GUI');
  return c;
 };
 const platform=()=>typeof currentPlatform!=='undefined'?currentPlatform:'ios';
 const transport=()=>window.getVpnTransport?.()||(()=>{try{return sessionStorage.getItem('tolfTransport')||'ikev2';}catch{return 'ikev2';}})();
 const key=p=>(p==='windows'?'tolfOpenConnectInstalled:':'tolfCiscoInstalled:')+p;
 window.isCiscoClientConfirmed=p=>{
  p=p||platform();if(!['ios','android','windows'].includes(p))return false;
  try{return localStorage.getItem(key(p))==='true';}catch{return remembered.has(p);}
 };
 window.getCiscoInstallCopy=copy;
 window.focusCiscoInstall=()=>{
  host.classList.remove('hidden');
  host.scrollIntoView?.({behavior:'smooth',block:'center'});
  host.querySelector?.('input')?.focus?.();
 };
 function render(){
  const c=copy(),p=platform();host.classList.toggle('hidden',transport()!=='anyconnect');
  host.replaceChildren();
  const title=document.createElement('h3');title.textContent=c.title;
  const app=document.createElement('a');app.className='button-link secondary';
  app.textContent=c.install;app.target='_blank';app.rel='noopener noreferrer';
  app.href=p==='ios'?'https://apps.apple.com/app/id1135064690':p==='android'?'https://play.google.com/store/apps/details?id=com.cisco.anyconnect.vpn.android.avf':'https://www.infradead.org/openconnect-gui/download/openconnect-gui-1.6.2-win64.exe';
  const label=document.createElement('label');label.className='cisco-install-confirm';
  const check=document.createElement('input');check.type='checkbox';check.checked=window.isCiscoClientConfirmed(p);
  check.addEventListener('change',()=>{
   if(check.checked)remembered.add(p);else remembered.delete(p);
   try{localStorage.setItem(key(p),String(check.checked));}catch{}
   window.dispatchEvent(new Event('tolf:cisco-install-confirmed'));render();
  });
  const text=document.createElement('span');text.textContent=c.confirmed;
  label.append(check,text);host.append(title,app,label);
  const blocked=transport()==='anyconnect'&&!window.isCiscoClientConfirmed(p);
  if(blocked){const note=document.createElement('p');note.className='card-description';note.textContent=c.blocked;host.append(note);}
  for(const id of ['quickSetupLink','manualSetupLink'])document.getElementById(id)?.setAttribute('aria-disabled',String(blocked));
 }
 for(const id of ['quickSetupLink','manualSetupLink']){
  document.getElementById(id)?.addEventListener('click',event=>{
   if(transport()==='anyconnect'&&!window.isCiscoClientConfirmed(platform())){
    event.preventDefault();event.stopImmediatePropagation();window.focusCiscoInstall();
   }
  },true);
 }
 for(const event of ['vpntransportchange','vpnplatformchange'])window.addEventListener(event,render);
 new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 render();
})();
