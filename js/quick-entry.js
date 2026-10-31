// Choosing a setup mode never starts setup or requires a protocol/client.
(() => {
 'use strict';
 const $=id=>document.getElementById(id);
 const card=$('quickSetupCard'),manual=$('vpnCard'),panel=$('quickModePanel');
 const quickTab=$('quickSetupLink'),manualTab=$('manualSetupLink'),start=$('quickStartLink');
 const notice=$('quickWindowsNotice');
 if(!card||!manual||!panel||!quickTab||!manualTab||!start||!notice)return;
 let enabled=false,mode=null,noticeOpen=false;
 const protocolChoices=new Map();let activeContext=null,restoring=false;
 const contextKey=()=>mode?currentPlatform+':'+mode:null;
 function restoreProtocol(){
  const next=contextKey();if(next===activeContext)return;
  activeContext=next;const choice=protocolChoices.get(next)||'';
  restoring=true;
  try{
   if(choice)$(choice==='ikev2'?'vpnTransportIkev2':'vpnTransportAnyConnect').click();
   else window.clearVpnTransportChoice?.();
  }finally{restoring=false;}
 }
 const words={
  ru:{label:'Способ настройки',quick:'Быстрая настройка',manual:'Ручная установка',start:'Начать быструю настройку',help:'Выберите протокол для быстрой настройки этого устройства. Точка входа будет предложена на следующем шаге.',title:'Быстрая настройка ',open:'Откройте vpn.tolf.is на устройстве ',choose:'Выберите «Быстрая настройка», затем протокол и нажмите «Начать быструю настройку».',device:'Настройки устанавливаются на том устройстве, на котором открыт сайт.'},
  en:{label:'Setup method',quick:'Quick setup',manual:'Manual setup',start:'Start quick setup',help:'Choose a protocol for quick setup of this device. An entry point will be suggested in the next step.',title:'Quick setup for ',open:'Open vpn.tolf.is on your ',choose:'Choose Quick setup, select a protocol and press Start quick setup.',device:'Settings are installed on the device where the website is open.'},
  lv:{label:'Iestatīšanas veids',quick:'Ātrā iestatīšana',manual:'Manuālā iestatīšana',start:'Sākt ātro iestatīšanu',help:'Izvēlieties protokolu šīs ierīces ātrajai iestatīšanai. Ieejas punkts tiks ieteikts nākamajā solī.',title:'Ātrā iestatīšana: ',open:'Atveriet vpn.tolf.is ierīcē ',choose:'Izvēlieties Ātrā iestatīšana, atlasiet protokolu un nospiediet Sākt ātro iestatīšanu.',device:'Iestatījumi tiek instalēti ierīcē, kurā vietne ir atvērta.'}
 };
 const tr=()=>words[document.documentElement.lang]||words.en;
 function nativePlatform(){
  const ua=navigator.userAgent||'';
  if(/Android/i.test(ua))return 'android';
  if(/Windows NT/i.test(ua)&&!/Windows Phone/i.test(ua))return 'windows';
  if(/iPhone|iPad|iPod/i.test(ua)||(/Mac/i.test(navigator.platform||'')&&navigator.maxTouchPoints>1))return 'ios';
  return null;
 }
 function renderNotice(){
  notice.classList.toggle('hidden',!noticeOpen);
  if(!noticeOpen)return;
  const c=tr(),device=currentPlatform==='windows'?'Windows':currentPlatform==='android'?'Android':'iPhone / iPad';
  const title=document.createElement('strong');title.textContent=c.title+device;
  const steps=document.createElement('ol');
  for(const text of [c.open+device+'.',c.choose,c.device]){const li=document.createElement('li');li.textContent=text;steps.append(li);}
  notice.replaceChildren(title,steps);
 }
 function render(){
  card.classList.toggle('hidden',!enabled||(typeof vpnInvitation!=='undefined'&&Boolean(vpnInvitation)));
  document.body.dataset.vpnSetupMode=mode||'';
  document.body.classList.toggle('manual-setup-open',mode==='manual');
  panel.hidden=mode!=='quick';
  manual.setAttribute('aria-hidden',String(mode!=='manual'));
  for(const [value,button] of [['quick',quickTab],['manual',manualTab]]){
   const selected=value===mode;
   button.setAttribute('aria-selected',String(selected));
   button.setAttribute('aria-disabled','false');button.disabled=false;
   button.tabIndex=selected||!mode&&value==='quick'?0:-1;
  }
  manualTab.setAttribute('aria-expanded',String(mode==='manual'));
  $('vpnSetupModes').setAttribute('aria-label',tr().label);
  quickTab.textContent=tr().quick;manualTab.textContent=tr().manual;
  start.textContent=tr().start;$('quickSetupHelp').textContent=tr().help;
  const protocol=window.getVpnTransport?.()||'';
  start.setAttribute('aria-disabled',String(!protocol));
  if(protocol)start.href='/quick/?protocol='+encodeURIComponent(protocol);else start.removeAttribute('href');
  renderNotice();
 }
 function select(next){
  if(!['quick','manual'].includes(next))return;
  mode=next;noticeOpen=false;
  restoreProtocol();
  if(location.hash==='#vpnCard'||location.hash==='#signedOutCard')history.replaceState(history.state,'',location.pathname+location.search);
  render();window.dispatchEvent(new Event('tolf:setup-mode-change'));
 }
 window.tolfSetupMode={get:()=>mode,select};
 // Keep both modes in the same My VPN surface, preserving all original controls.
 $('vpnPageTools').before(manual);
 quickTab.addEventListener('click',()=>select('quick'));
 manualTab.addEventListener('click',()=>select('manual'));
 $('vpnSetupModes').addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();
  const next=event.key==='Home'?'quick':event.key==='End'?'manual':mode==='quick'?'manual':'quick';
  select(next);(next==='quick'?quickTab:manualTab).focus();
 });
 start.addEventListener('click',event=>{
  const protocol=window.getVpnTransport?.()||'';
  if(mode!=='quick'||!protocol){event.preventDefault();document.querySelector('#vpnProtocolDropdown button')?.focus();return;}
  if(currentPlatform!==nativePlatform()){
   event.preventDefault();noticeOpen=true;renderNotice();return;
  }
  const url=new URL(start.href,location.href);
  url.searchParams.set('platform',currentPlatform);
  url.searchParams.set('v','setup-modes-20261031');
  try{
   sessionStorage.removeItem('quickClientHandoff');
   if(protocol==='anyconnect'&&window.isCiscoClientConfirmed?.(currentPlatform))
    sessionStorage.setItem('quickClientHandoff',JSON.stringify({platform:currentPlatform,createdAt:Date.now()}));
  }catch{}
  start.href=url.href;noticeOpen=false;renderNotice();
 });
 function fromHash(){if(location.hash==='#vpnCard'||location.hash==='#signedOutCard')select('manual');}
 window.addEventListener('hashchange',fromHash);
 window.addEventListener('vpnplatformchange',()=>{restoreProtocol();noticeOpen=false;render();});
 window.addEventListener('vpntransportchange',()=>{
  if(!restoring&&contextKey())protocolChoices.set(contextKey(),window.getVpnTransport?.()||'');
  noticeOpen=false;render();
 });
 new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 new MutationObserver(render).observe(manual,{attributes:true,attributeFilter:['class']});
 new MutationObserver(render).observe($('invitationCard'),{attributes:true,attributeFilter:['class']});
 fetch('https://api.tolf.is/quick-setup/capabilities',{credentials:'omit',cache:'no-store'})
  .then(r=>r.ok?r.json():null).then(data=>{enabled=data?.version===1;render();}).catch(()=>render());
 render();fromHash();
})();
