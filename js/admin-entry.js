// Put authenticated account controls into the VPN top navigation.
(() => {
  const nav=document.querySelector(".compact-header .header-navigation");
  const languages=nav?.querySelector(".language-switcher");
  const account=document.getElementById("accountNavigation");
  const signOut=document.getElementById("signOutButton");
  const title=document.querySelector(".compact-header .brand-copy");
  if(!nav||!languages||!account||!signOut||!title)return;
  account.className="vpn-header-account";
  signOut.classList.add("vpn-header-signout");
  nav.insertBefore(title,languages);
  nav.insertBefore(account,languages);
  languages.insertAdjacentElement("afterend",signOut);
  const labels={en:"My account",ru:"Личный кабинет",lv:"Mans konts"};
  function refresh(){const l=document.documentElement.lang||"en";account.textContent=labels[l]||labels.en;account.href="account/?lang="+l;}
  new MutationObserver(refresh).observe(document.documentElement,{attributes:true,attributeFilter:["lang"]});
  refresh();
})();