// Show the simple onboarding entry only after the matching server API is installed.
(() => {
 let enabled=false;
 const manualLink=document.getElementById('manualSetupLink');
 function openManual(){
  document.body.classList.add('manual-setup-open');
  manualLink.setAttribute('aria-expanded','true');
 }
 manualLink.setAttribute('aria-controls','vpnCard');
 manualLink.setAttribute('aria-expanded','false');
 manualLink.addEventListener('click',openManual);
 function handleHash(){if(location.hash==='#vpnCard'||location.hash==='#signedOutCard')openManual();}
 window.addEventListener('hashchange',handleHash);
 handleHash();
 const quickLink=document.getElementById('quickSetupLink');
 const notice=document.createElement('aside');
 notice.className='windows-setup-notice hidden';
 notice.id='quickWindowsNotice'; notice.setAttribute('role','status');
 quickLink.parentElement.after(notice);
 const copy={
  ru:['Быстрая настройка Windows','На компьютере Windows откройте vpn.tolf.is.','Выберите Windows, протокол IKEv2 и нажмите «Быстрая настройка».','Настройки устанавливаются на том компьютере, на котором открыт сайт.'],
  en:['Windows quick setup','Open vpn.tolf.is on your Windows computer.','Select Windows, IKEv2 and “Quick setup”.','The settings are installed on the computer where you opened the site.'],
  lv:['Windows ātrā iestatīšana','Windows datorā atveriet vpn.tolf.is.','Atlasiet Windows, IKEv2 un “Ātrā iestatīšana”.','Iestatījumi tiek instalēti datorā, kurā ir atvērta vietne.']
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
  const words=copy[document.documentElement.lang]||copy.en;
  const title=document.createElement('strong');title.textContent=words[0];
  const steps=document.createElement('ol');
  for(const word of words.slice(1)){const li=document.createElement('li');li.textContent=word;steps.append(li);}
  notice.replaceChildren(title,steps);
 }
 quickLink.addEventListener('click',event=>{
  const transport=window.getVpnTransport?.()||'ikev2';
  if(currentPlatform==='windows'&&transport==='ikev2'&&!nativeWindows()){
   event.preventDefault();noticeOpen=true;renderNotice();return;
  }
  const url=new URL(quickLink.href,location.href);
  url.searchParams.set('platform',currentPlatform);
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
