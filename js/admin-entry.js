// Header account controls. Match the authenticated controls on the TOLF home page.
(() => {
  const card = document.getElementById("vpnCard");
  const nav = document.querySelector(".compact-header .header-navigation");
  const languages = nav?.querySelector(".language-switcher");
  const account = document.getElementById("accountNavigation");
  const signOut = document.getElementById("signOutButton");
  if (!card || !nav || !languages || !account || !signOut) return;

  account.classList.add("vpn-header-account");
  nav.insertBefore(account, languages);

  const admin = document.createElement("a");
  admin.id = "vpnAdminLink";
  admin.href = "/admin/v1.3.html";
  admin.className = "vpn-header-admin hidden";
  nav.insertBefore(admin, languages);

  signOut.classList.add("vpn-header-signout");
  languages.insertAdjacentElement("afterend", signOut);

  const labels = {
    en:{account:"My TOLF account",admin:"Admin"},
    ru:{account:"Личный кабинет TOLF",admin:"Админ"},
    lv:{account:"Mans TOLF konts",admin:"Admin"}
  };
  function label() {
    const lang=document.documentElement.lang || "en";
    const c=labels[lang] || labels.en;
    account.textContent=c.account;
    account.href="account/?lang="+lang;
    admin.textContent=c.admin;
  }

  let epoch=0, visible=false;
  function check() {
    const now=!card.classList.contains("hidden");
    if (now===visible) return;
    visible=now;
    const own=++epoch;
    admin.classList.add("hidden");
    if (!now) return;
    fetch("https://api.tolf.is/admin/me",{
      credentials:"include",cache:"no-store",headers:{Accept:"application/json"}
    }).then(r=>r.ok?r.json():null).then(data=>{
      if (own===epoch && visible && data?.isAdmin===true) admin.classList.remove("hidden");
    }).catch(()=>{});
  }
  new MutationObserver(check).observe(card,{attributes:true,attributeFilter:["class"]});
  new MutationObserver(label).observe(document.documentElement,{attributes:true,attributeFilter:["lang"]});
  label(); check();
})();