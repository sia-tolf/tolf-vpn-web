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

document
  .getElementById("profileQrButton")
  ?.classList.replace("secondary", "constructive");

setLanguage(currentLanguage);
loadAccount();
