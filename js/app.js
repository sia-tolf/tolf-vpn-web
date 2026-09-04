languageEn.addEventListener(
  "click",
  () => setLanguage("en")
);

languageRu.addEventListener(
  "click",
  () => setLanguage("ru")
);

languageLv.addEventListener(
  "click",
  () => setLanguage("lv")
);

setLanguage(currentLanguage);
loadAccount();
