function renderPlatform() {
  const isIos = currentPlatform === "ios";

  platformIos.classList.toggle("active", isIos);
  platformAndroid.classList.toggle("active", !isIos);

  platformIos.setAttribute("aria-pressed", String(isIos));
  platformAndroid.setAttribute("aria-pressed", String(!isIos));

  generateProfileButton.dataset.i18n = isIos
    ? "generateInstallLink"
    : "generateStrongSwanProfile";

  installProfileButton.dataset.i18n = isIos
    ? "installAppleDevice"
    : "installAndroidDevice";

  if (typeof t === "function") {
    generateProfileButton.textContent =
      t(generateProfileButton.dataset.i18n);

    installProfileButton.textContent =
      t(installProfileButton.dataset.i18n);
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
