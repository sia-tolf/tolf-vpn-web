let previousMobilePlatform = currentPlatform === "android" ? "android" : "ios";

function renderPlatform() {
  const backButton = document.getElementById("windowsBackButton");
  if (typeof t === "function") {
    backButton.textContent = t(previousMobilePlatform === "android" ? "windowsBackAndroid" : "windowsBackIos");
  }
  backButton.disabled = vpnBusy;
  const isIos = currentPlatform === "ios";
  const isWindows = currentPlatform === "windows";
  const winButton = document.getElementById("platformWindows");
  winButton.classList.toggle("active", isWindows);
  winButton.setAttribute("aria-pressed", String(isWindows));
  document.getElementById("windowsPanel").classList.toggle("hidden", !isWindows);
  document.getElementById("legacyVpnPanel").classList.toggle("hidden", isWindows);
  if (typeof renderWindowsDevices === "function") renderWindowsDevices();

  platformIos.classList.toggle("active", isIos);
  platformAndroid.classList.toggle("active", currentPlatform === "android");

  platformIos.setAttribute("aria-pressed", String(isIos));
  platformAndroid.setAttribute("aria-pressed", String(currentPlatform === "android"));

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
  if (vpnBusy || !["ios", "android", "windows"].includes(platform)) {
    return;
  }

  const changed = currentPlatform !== platform;

  if (platform !== "windows") previousMobilePlatform = platform;
  currentPlatform = platform;
  localStorage.setItem("tolfPlatform", platform);

  renderPlatform();
  if (changed && platform === "windows" && typeof loadWindowsDevices === "function") loadWindowsDevices();

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

document.getElementById("platformWindows").addEventListener("click", () => setPlatform("windows"));

document.getElementById("windowsBackButton").addEventListener("click", () => setPlatform(previousMobilePlatform));

setPlatform(currentPlatform);
