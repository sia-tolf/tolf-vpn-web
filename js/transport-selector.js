// Step 1 of AnyConnect UI: switch only the VPN overview identity.
(() => {
  const selector = document.getElementById("vpnTransportSelector");
  const ikev2 = document.getElementById("vpnTransportIkev2");
  const anyConnect = document.getElementById("vpnTransportAnyConnect");
  const overviewTitle = document.getElementById("vpnOverviewTitle");

  if (!selector || !ikev2 || !anyConnect || !overviewTitle) return;

  let transport = "ikev2";
  let ikev2Server = null;

  function selectedServer() {
    return Array.from(typeof serverInputs !== "undefined" ? serverInputs : [])
      .find(input => input.checked)?.value || null;
  }

  function setPressed() {
    const isIkev2 = transport === "ikev2";
    ikev2.classList.toggle("active", isIkev2);
    anyConnect.classList.toggle("active", !isIkev2);
    ikev2.setAttribute("aria-pressed", String(isIkev2));
    anyConnect.setAttribute("aria-pressed", String(!isIkev2));
  }

  function render() {
    setPressed();

    const riga = document.getElementById("serverRiga");
    const moscow = document.getElementById("serverMoscow");

    if (transport === "ikev2") {
      overviewTitle.textContent = typeof t === "function"
        ? t("vpnOverviewTitle")
        : "VPN · IKEv2";

      if (riga) riga.disabled = false;
      if (moscow) moscow.disabled = false;

      const restore = ikev2Server === "moscow" ? moscow : riga;
      if (restore && !restore.checked) {
        restore.checked = true;
        if (typeof updateSelectedServerAddress === "function") {
          updateSelectedServerAddress();
        }
      }

      if (typeof lastVpnState !== "undefined" && lastVpnState) {
        renderVpnState(lastVpnState);
      }
      return;
    }

    overviewTitle.textContent = "VPN · AnyConnect";

    // AnyConnect currently has one entry point: Moscow.
    if (riga) riga.disabled = true;
    if (moscow) {
      moscow.disabled = false;
      if (!moscow.checked) {
        moscow.checked = true;
        if (typeof updateSelectedServerAddress === "function") {
          updateSelectedServerAddress();
        }
      }
    }

    if (typeof vpnServerName !== "undefined" && vpnServerName) {
      vpnServerName.textContent = typeof t === "function" ? t("cityMoscow") : "Moscow";
    }
    if (typeof vpnServerHost !== "undefined" && vpnServerHost) {
      vpnServerHost.textContent = "";
    }
    if (typeof serverRow !== "undefined" && serverRow) {
      serverRow.classList.remove("hidden");
    }

    // Username deliberately remains the existing VPN username.
  }

  ikev2.addEventListener("click", () => {
    transport = "ikev2";
    render();
  });

  anyConnect.addEventListener("click", () => {
    if (transport === "ikev2") {
      ikev2Server = selectedServer();
    }
    transport = "anyconnect";
    render();
  });

  new MutationObserver(render).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["lang"]
  });

  render();
})();
