// Measurement selection is independent of the VPN profile settings.
(() => {
  const links = [...document.querySelectorAll("[data-measurement-link]")];
  function update() {
    let server = typeof getSelectedServerKey === "function" ? getSelectedServerKey() : "riga";
    if (window.getVpnTransport?.() !== "anyconnect" && typeof currentPlatform !== "undefined" && currentPlatform === "windows")
      server = document.getElementById("windowsDeviceServer")?.value || server;
    for (const link of document.querySelectorAll('[data-billing-link]'))link.href='billing/?lang='+(document.documentElement.lang||'en');
    for (const link of links) link.href = "connection/?lang=" + (document.documentElement.lang || "en") + "&server=" + encodeURIComponent(server);
  }
  for (const link of links) link.addEventListener("click", update);
  new MutationObserver(update).observe(document.documentElement, {attributes:true,attributeFilter:["lang"]});
  update();
})();
