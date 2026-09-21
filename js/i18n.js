function t(key, replacements = {}) {
  let value =
    I18N[currentLanguage]?.[key] ??
    I18N.en[key] ??
    key;

  for (const [name, replacement] of Object.entries(replacements)) {
    value = value.replaceAll(`{${name}}`, replacement);
  }

  return value;
}

function setLanguage(language) {
  if (!["en", "ru", "lv"].includes(language)) {
    return;
  }

  currentLanguage = language;
  localStorage.setItem("tolfLanguage", language);
  document.documentElement.lang = language;
  const homeNavigation = document.getElementById("homeNavigation");
  if (homeNavigation) {
    homeNavigation.innerHTML =
      '‹ <span class="tolf-wordmark">TOLF</span>';
    homeNavigation.setAttribute("aria-label", {
      en: "TOLF home",
      ru: "На главную TOLF",
      lv: "Uz TOLF sākumlapu"
    }[language]);
    homeNavigation.href = "https://tolf.is/?lang=" + language;
  }

  const accountNavigation = document.getElementById("accountNavigation");
  if (accountNavigation) {
    accountNavigation.textContent = {en:"TOLF Account",ru:"Аккаунт TOLF",lv:"TOLF konts"}[language];
    accountNavigation.href = "account/?lang=" + language;
  }
  const helpNavigation = document.getElementById("helpNavigation");
  if (helpNavigation) {
    helpNavigation.textContent = { en: "Help", ru: "Помощь", lv: "Palīdzība" }[language];
    helpNavigation.href = "help.html?lang=" + language;
  }

  languageEn.classList.toggle(
    "active",
    language === "en"
  );

  languageRu.classList.toggle(
    "active",
    language === "ru"
  );

  languageLv.classList.toggle(
    "active",
    language === "lv"
  );

  document.querySelectorAll("[data-i18n]").forEach(element => {
    element.textContent = t(element.dataset.i18n);
  });

  if (lastVpnState) {
    renderVpnState(lastVpnState);
  }

  if (lastPasskeys.length) {
    renderPasskeys(lastPasskeys);
  }

  if (typeof renderInvitation === "function") renderInvitation();
  renderPromoState();
  renderLocalIdSettings();
  renderPlatform();

  if (typeof renderProfileSettings === "function") {
    renderProfileSettings();
  }

  if (typeof renderConnectionTestTarget === "function") {
    renderConnectionTestTarget();
  }

  if (typeof renderEntryPointRecommendation === "function") {
    renderEntryPointRecommendation();
  }
}

function confirmLocalized(
  titleKey,
  bodyKey,
  replacements = {}
) {
  return window.confirm(
    t(titleKey) +
    "\n\n" +
    t(bodyKey, replacements)
  );
}
