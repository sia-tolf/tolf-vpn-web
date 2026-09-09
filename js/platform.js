function renderPlatform() {
  const isIos = currentPlatform === "ios";

  platformIos.classList.toggle("active", isIos);
  platformAndroid.classList.toggle("active", !isIos);

  platformIos.setAttribute("aria-pressed", String(isIos));
  platformAndroid.setAttribute("aria-pressed", String(!isIos));

  generateProfileButton.dataset.i18n = isIos
    ? "generateAppleProfile"
    : "generateStrongSwanProfile";

  installProfileButton.dataset.i18n = isIos
    ? "installAppleProfile"
    : "openAndroidProfile";

  shareProfileButton.dataset.i18n = isIos
    ? "shareAppleProfile"
    : "shareAndroidProfile";

  if (typeof t === "function") {
    generateProfileButton.textContent =
      t(generateProfileButton.dataset.i18n);

    installProfileButton.textContent =
      t(installProfileButton.dataset.i18n);

    shareProfileButton.textContent =
      t(shareProfileButton.dataset.i18n);
  }

  if (onDemandSection) {
    onDemandSection.classList.toggle("hidden", !isIos);
  }

  if (onDemandAndroidNote) {
    onDemandAndroidNote.classList.toggle("hidden", isIos);
  }
}

function setPlatform(platform) {
  if (platform !== "ios" && platform !== "android") {
    return;
  }

  const changed = currentPlatform !== platform;

  currentPlatform = platform;
  localStorage.setItem("tolfPlatform", platform);

  renderPlatform();

  if (changed && typeof setInstallLink === "function") {
    setInstallLink(null);
    vpnMessage.textContent = "";
    vpnMessage.className = "message";
  }
}

platformIos.addEventListener(
  "click",
  () => setPlatform("ios")
);

platformAndroid.addEventListener(
  "click",
  () => setPlatform("android")
);

setPlatform(currentPlatform);
