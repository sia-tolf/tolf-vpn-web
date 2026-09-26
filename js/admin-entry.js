// UI convenience only. Every admin API request independently checks the role.
(() => {
  const card = document.getElementById("vpnCard");
  const heading = card?.querySelector(".card-topline");
  const signOut = document.getElementById("signOutButton");
  if (!card || !heading || !signOut || document.getElementById("vpnAdminLink")) return;

  const menu = document.createElement("details");
  menu.className = "vpn-account-menu";
  const toggle = document.createElement("summary");
  const title = document.createElement("span");
  toggle.append(title);
  const actions = document.createElement("div");
  actions.className = "vpn-account-actions";
  menu.append(toggle, actions);

  // Align dropdown left edge with viewport center.
  function alignAccountDropdown() {
    if (!menu.open) return;
    const center = document.documentElement.clientWidth / 2;
    const width = menu.getBoundingClientRect().right - center;
    if (width > 0) {
      actions.style.setProperty("width", width + "px", "important");
    }
  }
  menu.addEventListener("toggle", alignAccountDropdown);
  window.addEventListener("resize", alignAccountDropdown);

  heading.insertBefore(menu, signOut);
  const account = document.getElementById("accountNavigation");
  if (account) actions.append(account);
  const labels = { en: "Admin", ru: "Админ", lv: "Admin" };
  const link = document.createElement("a");
  link.id = "vpnAdminLink";
  link.href = "/admin/v1.3.html";
  link.className = "hidden";
  actions.append(link, signOut);
  function closeMenu(focus = false) {
    if (!menu.open) return;
    menu.open = false;
    if (focus) toggle.focus();
  }
  document.addEventListener("pointerdown", event => {
    if (!menu.contains(event.target)) closeMenu();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && menu.open) { closeMenu(true); event.preventDefault(); }
  });
  document.addEventListener("focusin", event => {
    if (!menu.contains(event.target)) closeMenu();
  });
  actions.addEventListener("click", event => {
    if (event.target.closest("a, button")) closeMenu();
  });

  let epoch = 0;
  let visible = false;
  function label() {
    const lang = document.documentElement.lang;
    link.textContent = labels[lang] || labels.en;
    title.textContent = {en:"Account",ru:"Аккаунт",lv:"Konts"}[lang] || "Account";
    for (const code of ["en","ru","lv"]) {
      document.getElementById("language" + code[0].toUpperCase() + code.slice(1))
        ?.setAttribute("aria-pressed", String(code === lang));
    }
  }
  function check() {
    const now = !card.classList.contains("hidden");
    if (now === visible) return;
    visible = now;
    const own = ++epoch;
    link.classList.add("hidden");
    if (!now) { closeMenu(); return; }
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

