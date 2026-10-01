// Step 1 of AnyConnect UI: switch only the VPN overview identity.
(() => {
  const selector = document.getElementById("vpnTransportSelector");
  const ikev2 = document.getElementById("vpnTransportIkev2");
  const anyConnect = document.getElementById("vpnTransportAnyConnect");
  const overviewTitle = document.getElementById("vpnOverviewTitle");

  if (!selector || !ikev2 || !anyConnect || !overviewTitle) return;

  let transport = "ikev2";

  function setPressed() {
    const isIkev2 = transport === "ikev2";
    ikev2.classList.toggle("active", isIkev2);
    anyConnect.classList.toggle("active", !isIkev2);
    ikev2.setAttribute("aria-pressed", String(isIkev2));
    anyConnect.setAttribute("aria-pressed", String(!isIkev2));
  }

  function render() {
    setPressed();

    if (transport === "ikev2") {
      overviewTitle.textContent = typeof t === "function"
        ? t("vpnOverviewTitle")
        : "VPN · IKEv2";

      if (typeof lastVpnState !== "undefined" && lastVpnState) {
        renderVpnState(lastVpnState);
      }
      return;
    }

    overviewTitle.textContent = "VPN · AnyConnect";

    // AnyConnect currently has one entry point: Moscow.
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
    transport = "anyconnect";
    render();
  });

  new MutationObserver(render).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["lang"]
  });

  render();
})();
