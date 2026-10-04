// Header account controls. Match the TOLF home header; no Admin control in the VPN header.
(() => {
  const card=document.getElementById("vpnCard");
  const nav=document.querySelector(".compact-header .header-navigation");
  const languages=nav?.querySelector(".language-switcher");
  const account=document.getElementById("accountNavigation");
  const signOut=document.getElementById("signOutButton");
  if(!card||!nav||!languages||!account||!signOut)return;
  account.classList.add("vpn-header-account");
  nav.insertBefore(account,languages);
  signOut.classList.add("vpn-header-signout");
  languages.insertAdjacentElement("afterend",signOut);
  const labels={en:"My account",ru:"Личный кабинет",lv:"Mans konts"};
  function label(){const lang=document.documentElement.lang||"en";account.textContent=labels[lang]||labels.en;account.href="account/?lang="+lang;}
  new MutationObserver(label).observe(document.documentElement,{attributes:true,attributeFilter:["lang"]});
  label();
})();