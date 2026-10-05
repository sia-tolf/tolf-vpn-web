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
