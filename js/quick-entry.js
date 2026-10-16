// Show the simple onboarding entry only after the matching server API is installed.
(() => {
 let enabled=false;
 const manualLink=document.getElementById('manualSetupLink');
 function openManual(){
  document.body.classList.add('manual-setup-open');
  manualLink.setAttribute('aria-expanded','true');
  noticeOpen=false;
  renderNotice();
 }
 manualLink.setAttribute('aria-controls','vpnCard');
 manualLink.setAttribute('aria-expanded','false');
 manualLink.addEventListener('click',openManual);
 function handleHash(){if(location.hash==='#vpnCard'||location.hash==='#signedOutCard')openManual();}
 window.addEventListener('hashchange',handleHash);
 const quickLink=document.getElementById('quickSetupLink');
 const notice=document.createElement('aside');
 notice.className='windows-setup-notice hidden';
 notice.id='quickWindowsNotice'; notice.setAttribute('role','status');
 quickLink.parentElement.after(notice);
 const copy={
  ru:['Быстрая настройка Windows','На компьютере Windows откройте vpn.tolf.is.','Выберите Windows, нужный протокол и нажмите «Быстрая настройка».','Настройки устанавливаются на том компьютере, на котором открыт сайт.'],
  en:['Windows quick setup','Open vpn.tolf.is on your Windows computer.','Select Windows, the desired protocol and “Quick setup”.','The settings are installed on the computer where you opened the site.'],
  lv:['Windows ātrā iestatīšana','Windows datorā atveriet vpn.tolf.is.','Atlasiet Windows, vajadzīgo protokolu un “Ātrā iestatīšana”.','Iestatījumi tiek instalēti datorā, kurā ir atvērta vietne.']
 };
 let noticeOpen=false;
 function nativeWindows(){
  const ua=navigator.userAgent||'';
  return /Windows NT/i.test(ua)&&!/Android|iPhone|iPad|iPod|Windows Phone/i.test(ua)
   &&!(/Mac/i.test(navigator.platform||'')&&navigator.maxTouchPoints>1);
 }
 function renderNotice(){
  notice.classList.toggle('hidden',!noticeOpen);
  if(!noticeOpen)return;
  const language=document.documentElement.lang;
  const mobileCopy={
   ru:['Быстрая настройка '+(currentPlatform==='android'?'Android':'iPhone / iPad'),
       'Откройте vpn.tolf.is на устройстве '+(currentPlatform==='android'?'Android':'iPhone или iPad')+'.',
       'Выберите AnyConnect, подтвердите установку Cisco Secure Client и нажмите «Быстрая настройка».',
       'Быстрая настройка выполняется на том устройстве, на котором открыт сайт.'],
   en:['Quick setup for '+(currentPlatform==='android'?'Android':'iPhone / iPad'),
       'Open vpn.tolf.is on your '+(currentPlatform==='android'?'Android device':'iPhone or iPad')+'.',
       'Select AnyConnect, confirm Cisco Secure Client installation and select “Quick setup”.',
       'Quick setup runs on the device where the website is open.'],
   lv:[(currentPlatform==='android'?'Android':'iPhone / iPad')+' ātrā iestatīšana',
       'Atveriet vpn.tolf.is '+(currentPlatform==='android'?'Android ierīcē':'iPhone vai iPad')+'.',
       'Atlasiet AnyConnect, apstipriniet Cisco Secure Client instalēšanu un nospiediet “Ātrā iestatīšana”.',
       'Ātrā iestatīšana notiek ierīcē, kurā atvērta vietne.']
  };
  const words=currentPlatform==='windows'?(copy[language]||copy.en):(mobileCopy[language]||mobileCopy.en);
  const title=document.createElement('strong');title.textContent=words[0];
  const steps=document.createElement('ol');
  for(const word of words.slice(1)){const li=document.createElement('li');li.textContent=word;steps.append(li);}
  notice.replaceChildren(title,steps);
 }
 handleHash();
 quickLink.addEventListener('click',event=>{
  document.body.classList.remove('manual-setup-open');
  manualLink.setAttribute('aria-expanded','false');
  if(location.hash==='#vpnCard'||location.hash==='#signedOutCard')
   history.replaceState(history.state,'',location.pathname+location.search);
  const transport=window.getVpnTransport?.()||'ikev2';
  const ua=navigator.userAgent||'';
  const nativePlatform=/Android/i.test(ua)?'android':nativeWindows()?'windows':'ios';
  if((currentPlatform==='windows'&&!nativeWindows()) ||
     (transport==='anyconnect'&&currentPlatform!==nativePlatform)){
   event.preventDefault();noticeOpen=true;renderNotice();return;
  }
  const url=new URL(quickLink.href,location.href);
  url.searchParams.set('platform',currentPlatform);
  url.searchParams.set('v','windows-platform-20261014');
  // One-use confirmation for this navigation, never a remembered installation.
  try{
   sessionStorage.removeItem('quickClientHandoff');
   if(transport==='anyconnect'&&window.isCiscoClientConfirmed?.(currentPlatform))
    sessionStorage.setItem('quickClientHandoff',JSON.stringify({platform:currentPlatform,createdAt:Date.now()}));
  }catch{}
  quickLink.href=url.href;noticeOpen=false;renderNotice();
 });
 window.addEventListener('vpnplatformchange',()=>{noticeOpen=false;renderNotice();});
 window.addEventListener('vpntransportchange',()=>{noticeOpen=false;renderNotice();});
 new MutationObserver(renderNotice).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 const card=document.getElementById('quickSetupCard');
 new MutationObserver(()=>render()).observe(document.getElementById('vpnCard'),{attributes:true,attributeFilter:['class']});
 const invitationCard=document.getElementById('invitationCard');
 function invitation(){return typeof vpnInvitation!=='undefined' && Boolean(vpnInvitation);}
 function render(){
 card.classList.toggle('hidden',!enabled || invitation());
 document.getElementById('manualSetupLink').href=document.getElementById('vpnCard').classList.contains('hidden')?'#signedOutCard':'#vpnCard';
}
 new MutationObserver(render).observe(invitationCard,{attributes:true,attributeFilter:['class']});
 fetch('https://api.tolf.is/quick-setup/capabilities',{credentials:'omit',cache:'no-store'})
 .then(r=>r.ok?r.json():null).then(data=>{
  enabled=data?.version===1;
  render();
 }).catch(render);
})();
