// Manual confirmation of Cisco installation on this browser/device platform.
(() => {
 const host=document.getElementById('ciscoClientInstall');
 if(!host)return;
 const ua=navigator.userAgent||'';
 const nativePlatform=/Android/i.test(ua)?'android':/Windows NT/i.test(ua)?'windows':/iPhone|iPad|iPod/i.test(ua)||(/Mac/i.test(navigator.platform||'')&&navigator.maxTouchPoints>1)?'ios':null;
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
  ru:{title:'1. Установите Cisco Secure Client (AnyConnect).',install:'Установить Cisco Secure Client',confirmed:'Cisco Secure Client установлен',blocked:'Чтобы продолжить, подтвердите установку Cisco Secure Client в ручной настройке.',back:'К подтверждению установки',link:'Ссылка на установку',copy:'Копировать ссылку',copied:'Ссылка скопирована',copyFailed:'Не удалось скопировать. Выделенная ссылка доступна для копирования вручную.'},
  en:{title:'1. Install Cisco Secure Client (AnyConnect).',install:'Install Cisco Secure Client',confirmed:'Cisco Secure Client is installed',blocked:'Confirm Cisco Secure Client installation in manual setup to continue.',back:'Confirm installation',link:'Installation link',copy:'Copy link',copied:'Link copied',copyFailed:'Could not copy. Copy the selected link manually.'},
  lv:{title:'1. Instalējiet Cisco Secure Client (AnyConnect).',install:'Instalēt Cisco Secure Client',confirmed:'Cisco Secure Client ir instalēts',blocked:'Lai turpinātu, manuālajā iestatīšanā apstipriniet Cisco Secure Client instalēšanu.',back:'Apstiprināt instalēšanu',link:'Instalēšanas saite',copy:'Kopēt saiti',copied:'Saite nokopēta',copyFailed:'Neizdevās nokopēt. Nokopējiet atlasīto saiti manuāli.'}
 };
 const copy=()=>{
  const c={...(texts[document.documentElement.lang]||texts.en)};
  if(needsStrongSwan())for(const key of ['title','install','confirmed','blocked'])c[key]=c[key].replaceAll('Cisco Secure Client','strongSwan VPN Client').replace(' (AnyConnect)',' (IKEv2)');
  if(platform()==='windows')for(const key of ['title','install','confirmed','blocked'])c[key]=c[key].replaceAll('Cisco Secure Client','OpenConnect GUI');
  const store=platform()==='ios'?'App Store':platform()==='android'?'Google Play':null;
  if(store){
   const language=document.documentElement.lang;
   const suffix=language==='ru'?' из '+store:language==='lv'?' no '+store:' from '+store;
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
  let installControl=app;
  if(nativePlatform!==p){
   const field=document.createElement('div');field.className='cisco-install-link';
   const input=document.createElement('input');input.type='text';input.readOnly=true;
   input.value=app.href;input.setAttribute('aria-label',c.link);input.spellcheck=false;
   const button=document.createElement('button');button.type='button';button.className='oc-copy cisco-copy-link';
   button.setAttribute('aria-label',c.copy);button.title=c.copy;
   const glyph=document.createElement('span');glyph.className='oc-copy-glyph';
   glyph.setAttribute('aria-hidden','true');button.append(glyph);
   const status=document.createElement('span');status.className='cisco-copy-status';status.setAttribute('role','status');
   button.addEventListener('click',async()=>{
    try{
     if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(input.value);
     else{input.focus();input.select();if(!document.execCommand('copy'))throw new Error('copy');}
     status.textContent=c.copied;
    }catch{input.focus();input.select();status.textContent=c.copyFailed;}
   });
   field.append(input,button,status);installControl=field;
  }
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
  label.append(check,text);host.append(title,installControl,label);
  const blocked=!transport();
  for(const id of ['quickSetupLink','manualSetupLink'])document.getElementById(id)?.setAttribute('aria-disabled',String(blocked));
 }
 for(const id of ['quickSetupLink','manualSetupLink']){
  document.getElementById(id)?.addEventListener('click',event=>{
   if(!transport()){
    event.preventDefault();event.stopImmediatePropagation();document.querySelector('#vpnProtocolDropdown button')?.focus();return;
   }
  },true);
 }
 let lastTransport=transport();
 let lastPlatform=platform();
 function selectionChanged(){
  const next=transport(),nextPlatform=platform();
  if((next!==lastTransport||nextPlatform!==lastPlatform)&&needsApp()){
   if(needsStrongSwan()){
    strongSwanConfirmed=false;
    try{sessionStorage.removeItem('tolfStrongSwanInstalled');}catch{}
   }else{
    remembered.delete(platform());
    try{sessionStorage.removeItem(confirmationKey(platform()));}catch{}
   }
  }
  lastTransport=next;
  lastPlatform=nextPlatform;
  render();
 }
 window.addEventListener('vpntransportchange',selectionChanged);
 window.addEventListener('vpnplatformchange',selectionChanged);
 window.addEventListener('pageshow',render);
 new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 render();
})();
