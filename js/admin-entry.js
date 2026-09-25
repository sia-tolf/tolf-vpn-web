// UI convenience only. Every admin API request independently checks the role.
(() => {
  const card = document.getElementById("vpnCard");
  const heading = card?.querySelector(".card-topline");
  const signOut = document.getElementById("signOutButton");
  if (!card || !heading || !signOut || document.getElementById("vpnAdminLink")) return;

  const actions = document.createElement("div");
  actions.className = "vpn-account-actions";
  heading.insertBefore(actions, signOut);
  actions.appendChild(signOut);

  const labels = { en: "Administration", ru: "Администрирование", lv: "Administrēšana" };
  const link = document.createElement("a");
  link.id = "vpnAdminLink";
  link.href = "/admin/v1.3.html";
  link.className = "button-link secondary vpn-administration-button hidden";
  actions.insertBefore(link, signOut);

  const account = document.getElementById("accountNavigation");
  if (account) {
    account.classList.add("sign-out-button");
    actions.insertBefore(account, signOut);
  }

  let epoch = 0;
  let visible = false;
  function label() {
    link.textContent = labels[document.documentElement.lang] || labels.en;
  }
  function check() {
    const now = !card.classList.contains("hidden");
    if (now === visible) return;
    visible = now;
    const own = ++epoch;
    link.classList.add("hidden");
    if (!now) return;
    fetch("https://api.tolf.is/admin/me", {
      credentials: "include", cache: "no-store", headers: { Accept: "application/json" }
    }).then(response => response.ok ? response.json() : null).then(data => {
      if (own === epoch && visible && data?.isAdmin === true) link.classList.remove("hidden");
    }).catch(() => {});
  }
  new MutationObserver(check).observe(card, { attributes: true, attributeFilter: ["class"] });
  new MutationObserver(label).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  label();
  check();
})();
