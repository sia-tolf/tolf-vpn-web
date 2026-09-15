// Enable new-account onboarding only after the matching server API is installed.
(() => {
 let enabled=false;
 const button=document.getElementById('createAccountButton');
 const labels={ru:'Создать аккаунт и настроить VPN',en:'Create account and set up VPN',lv:'Izveidot kontu un iestatīt VPN'};
 function invitation(){return typeof vpnInvitation!=='undefined' && Boolean(vpnInvitation);}
 button.addEventListener('click',event=>{
  if(!enabled || invitation())return;
  event.preventDefault();event.stopImmediatePropagation();location.assign('/quick/');
 },true);
 fetch('https://api.tolf.is/quick-setup/capabilities',{credentials:'omit',cache:'no-store'})
 .then(r=>r.ok?r.json():null).then(data=>{
  enabled=data?.version===1;
  if(!enabled || invitation())return;
  const label=()=>{if(!invitation())button.textContent=labels[document.documentElement.lang]||labels.en;};
  label();new MutationObserver(label).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 }).catch(()=>{});
})();
