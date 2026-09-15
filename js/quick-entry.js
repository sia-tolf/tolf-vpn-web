// Show the simple onboarding entry only after the matching server API is installed.
(() => {
 let enabled=false;
 const card=document.getElementById('quickSetupCard');
 const signedOut=document.getElementById('signedOutCard');
 const invitationCard=document.getElementById('invitationCard');
 function invitation(){return typeof vpnInvitation!=='undefined' && Boolean(vpnInvitation);}
 function render(){card.classList.toggle('hidden',!enabled || invitation() || signedOut.classList.contains('hidden'));}
 new MutationObserver(render).observe(signedOut,{attributes:true,attributeFilter:['class']});
 new MutationObserver(render).observe(invitationCard,{attributes:true,attributeFilter:['class']});
 fetch('https://api.tolf.is/quick-setup/capabilities',{credentials:'omit',cache:'no-store'})
 .then(r=>r.ok?r.json():null).then(data=>{
  enabled=data?.version===1;
  render();
 }).catch(render);
})();
