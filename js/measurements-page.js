// This page owns its selection; it never changes a VPN profile or connection.
const serverInputs = [];
const connectionTestButton = document.getElementById("connectionTestButton");
const connectionTestTitle = document.getElementById("connectionTestTitle");
const connectionTestStatus = document.getElementById("connectionTestStatus");
const connectionTestLatency = document.getElementById("connectionTestLatency");
const connectionTestJitter = document.getElementById("connectionTestJitter");
const connectionTestDownload = document.getElementById("connectionTestDownload");
const connectionTestUpload = document.getElementById("connectionTestUpload");
function t(key, replacements = {}) {
  let value = I18N[currentLanguage]?.[key] ?? I18N.en[key] ?? key;
  for (const [name, replacement] of Object.entries(replacements)) value = value.replaceAll("{" + name + "}", replacement);
  return value;
}
(() => {
  const server = document.getElementById("measurementServer");
  const mode = document.getElementById("measurementMode");
  const cancel = document.getElementById("measurementCancel");
  const vpnConfirmation = document.getElementById("measurementVpnConfirmation");
  const vpnConnected = document.getElementById("measurementVpnConnected");
  const vpnConfirmationText = document.getElementById("measurementVpnConfirmationText");
  const storage = {get(key) {try {return localStorage.getItem(key);} catch {return null;}},
    set(key, value) {try {localStorage.setItem(key, value);} catch {}}};
  const url = new URL(location.href);
  const selected = url.searchParams.get("server") || storage.get("tolfMeasurementServer");
  server.value = ["riga", "moscow", "us"].includes(selected) ? selected : "riga";
  const selectedMode = url.searchParams.get("mode") || storage.get("tolfMeasurementMode");
  mode.value = ["direct", "vpn"].includes(selectedMode) ? selectedMode : "vpn";
  let busy = false;
  const vpnUnavailable = () => mode.value === "vpn" && typeof MEASUREMENT_TARGETS !== "undefined" && MEASUREMENT_TARGETS[server.value]?.vpnReady === false;
  window.updateMeasurementControls = running => {
    busy = running;
    server.disabled = mode.disabled = running;
    cancel.hidden = !running;
    vpnConfirmation.hidden = mode.value !== "vpn";
    vpnConnected.disabled = running || vpnUnavailable();
    connectionTestButton.disabled = running || vpnUnavailable() || mode.value === "vpn" && !vpnConnected.checked;
  };
  window.canStartConnectionMeasurement = () => {
    return !busy && !vpnUnavailable() && (mode.value !== "vpn" || vpnConnected.checked);
  };
  function render() {
    document.documentElement.lang = currentLanguage;
    document.title = t("connectionCheckTitle") + " — TOLF";
    for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
    for (const button of document.querySelectorAll("[data-language]")) {
      const active = button.dataset.language === currentLanguage;
      button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active));
    }
    document.getElementById("measurementBack").href = "../?lang=" + currentLanguage;
    const cityKey = {riga:"cityRiga", moscow:"cityMoscow", us:"cityNewYork"}[server.value];
    vpnConfirmationText.textContent = t("measurementVpnConnected", {city:t(cityKey)});
    document.getElementById("measurementModeHelp").textContent = t(vpnUnavailable() ? "measurementVpnNotReady" : mode.value === "direct" ? "measurementDirectHelp" : "measurementVpnHelp");
    renderConnectionTestTarget();
    if (vpnUnavailable()) {connectionTestStatus.textContent = t("connectionTestUnavailable"); connectionTestStatus.className = "vpn-overview-updated";}
    window.updateMeasurementControls(busy);
  }
  function contextChanged() {
    vpnConnected.checked = false;
    resetConnectionTestContext();
    storage.set("tolfMeasurementServer", server.value);
    storage.set("tolfMeasurementMode", mode.value);
    const next = new URL(location.href);
    next.searchParams.set("server", server.value); next.searchParams.set("mode", mode.value);
    history.replaceState(null, "", next.pathname + next.search + next.hash);
    render();
    window.dispatchEvent(new CustomEvent("tolf:measurement-selection-changed"));
  }
  for (const select of [server, mode]) select.addEventListener("change", contextChanged);
  vpnConnected.addEventListener("change", () => window.updateMeasurementControls(busy));
  cancel.addEventListener("click", () => {resetConnectionTestContext(); render();});
  for (const button of document.querySelectorAll("[data-language]")) button.addEventListener("click", () => {
    currentLanguage = button.dataset.language; storage.set("tolfLanguage", currentLanguage);
    const next = new URL(location.href); next.searchParams.set("lang", currentLanguage);
    history.replaceState(null, "", next.pathname + next.search + next.hash); render();
  });
  window.addEventListener("online", () => {vpnConnected.checked = false; window.updateMeasurementControls(busy);});
  window.addEventListener("pageshow", () => {vpnConnected.checked = false; render();});
  document.addEventListener("DOMContentLoaded", render, {once:true});
})();
