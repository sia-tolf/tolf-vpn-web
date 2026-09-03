function t(key, replacements = {}) {
  let value = I18N[currentLanguage]?.[key] ?? I18N.en[key] ?? key;

  for (const [name, replacement] of Object.entries(replacements)) {
    value = value.replaceAll(`{${name}}`, replacement);
  }

  return value;
}

function setLanguage(language) {
  if (language !== "en" && language !== "ru") return;

  currentLanguage = language;
  localStorage.setItem("tolfLanguage", language);
  document.documentElement.lang = language;

  languageEn.classList.toggle("active", language === "en");
  languageRu.classList.toggle("active", language === "ru");

  document.querySelectorAll("[data-i18n]").forEach(element => {
    element.textContent = t(element.dataset.i18n);
  });

  if (lastVpnState) renderVpnState(lastVpnState);
  if (lastPasskeys.length) renderPasskeys(lastPasskeys);
}

function confirmLocalized(titleKey, bodyKey, replacements = {}) {
  return window.confirm(t(titleKey) + "\n\n" + t(bodyKey, replacements));
}

languageEn.addEventListener("click", () => setLanguage("en"));
languageRu.addEventListener("click", () => setLanguage("ru"));
