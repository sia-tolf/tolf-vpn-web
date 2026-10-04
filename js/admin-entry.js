// Put authenticated account controls into the VPN top navigation.
(() => {
  const nav=document.querySelector(".compact-header .header-navigation");
  const languages=nav?.querySelector(".language-switcher");
  const account=document.getElementById("accountNavigation");
  const signOut=document.getElementById("signOutButton");
  if(!nav||!languages||!account||!signOut)return;
  account.className="vpn-header-account";
  signOut.classList.add("vpn-header-signout");
  nav.insertBefore(account,languages);
  languages.insertAdjacentElement("afterend",signOut);
  const labels={en:"My account",ru:"Личный кабинет",lv:"Mans konts"};
  function lang(){return document.documentElement.lang||"en";}
  function placeTitle(){
    if(!matchMedia("(min-width:700px)").matches)return;
    const home=document.getElementById("homeNavigation");
    const title=document.querySelector(".compact-header .brand-copy");
    if(!home||!title)return;
    const n=nav.getBoundingClientRect(), h=home.getBoundingClientRect(), a=account.getBoundingClientRect();
    title.style.left=(((h.right+a.left)/2)-n.left)+"px";
  }
  function refresh(){const l=lang();account.textContent=labels[l]||labels.en;account.href="account/?lang="+l;requestAnimationFrame(placeTitle);}
  new MutationObserver(refresh).observe(document.documentElement,{attributes:true,attributeFilter:["lang"]});
  window.addEventListener("resize",placeTitle);
  refresh();
})();