// AnyConnect UI, built incrementally alongside the existing IKEv2 UI.
(() => {
  const selector = document.getElementById("vpnTransportSelector");
  const ikev2 = document.getElementById("vpnTransportIkev2");
  const anyConnect = document.getElementById("vpnTransportAnyConnect");
  const overviewTitle = document.getElementById("vpnOverviewTitle");
  const modeRow = document.getElementById("anyConnectModeRow");
  const modeLabel = document.getElementById("anyConnectModeLabel");
  const modeHelp = document.getElementById("anyConnectModeHelp");
  const modeStatus = document.getElementById("anyConnectModeStatus");
  const modeButtons = Array.from(document.querySelectorAll(".anyconnect-mode-button"));

  if (!selector || !ikev2 || !anyConnect || !overviewTitle) return;

  const device = () => window.ocAccess?.selected() || null;
  const endpoint = (id, action) => `${API}/oc/access/devices/${encodeURIComponent(id)}/${action}`;
  let selectionToken = 0;
  let transport = "ikev2";
  window.getVpnTransport = () => transport;
  let ikev2Server = null;
  let anyConnectMode = "auto";
  let policyLoaded = false;
  let policyBusy = false;
  let savedStatusTimer = null;
  let policyConfirmed = false;
  let sessionConnected = false;
  let sessionInFlight = false;
  let sessionRequestToken = 0;
  let sessionStatus = "checking";
  window.getAnyConnectSessionStatus = () => ({id: device()?.id, status: sessionStatus});
  function setSessionStatus(status) {
    sessionStatus = status;
    window.updateAnyConnectSessionStatus?.();
  }

  const COPY = {
    en: {
      country: "Russia",
      protocol: "Protocol",
      mode: "Routing",
      saved: "Saved",
      saving: "Saving…",
      failed: "Could not save",
      loading: "Loading…",
      autoLabel: "Auto",
      auto: ["RU → Moscow", "rest → Riga"],
      ru: ["All traffic", "→ Moscow"],
      lv: ["All traffic", "→ Riga"],
      yt: ["RU + YouTube → Moscow", "rest → Riga"]
    },
    ru: {
      country: "Россия",
      protocol: "Протокол",
      mode: "Маршрутизация",
      saved: "Сохранено",
      saving: "Сохранение…",
      failed: "Не удалось сохранить",
      loading: "Загрузка…",
      autoLabel: "Авто",
      auto: ["RU → Москва", "остальное → Рига"],
      ru: ["Весь трафик", "→ Москва"],
      lv: ["Весь трафик", "→ Рига"],
      yt: ["RU + YouTube → Москва", "остальное → Рига"]
    },
    lv: {
      country: "Krievija",
      protocol: "Protokols",
      mode: "Maršrutēšana",
      saved: "Saglabāts",
      saving: "Saglabāšana…",
      failed: "Neizdevās saglabāt",
      loading: "Ielāde…",
      autoLabel: "Automātiski",
      auto: ["RU → Maskava", "pārējais → Rīga"],
      ru: ["Visa datplūsma", "→ Maskava"],
      lv: ["Visa datplūsma", "→ Rīga"],
      yt: ["RU + YouTube → Maskava", "pārējais → Rīga"]
    }
  };

  function lang() {
    const code = (document.documentElement.lang || "en").toLowerCase();
    return COPY[code] ? code : "en";
  }

  function copy() {
    return COPY[lang()];
  }

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

  function renderMode() {
    if (!modeRow) return;
    modeRow.classList.toggle("hidden", transport !== "anyconnect");
    if (transport !== "anyconnect") return;

    const c = copy();
    if (modeLabel) modeLabel.textContent = c.mode;
    const autoButton = document.getElementById("anyConnectModeAuto");
    if (autoButton) autoButton.textContent = c.autoLabel;
    for (const button of modeButtons) {
      const active = button.dataset.mode === anyConnectMode;
      button.classList.toggle("active", active);
      button.setAttribute("aria-checked", String(active));
      button.disabled = policyBusy || !device();
    }
    const controls = document.getElementById("anyConnectModeSelector");
    controls?.classList.toggle("policy-confirmed",
      policyLoaded && !policyBusy && sessionConnected);

    if (modeHelp) {
      const lines = anyConnectMode ? c[anyConnectMode] : null;
      modeHelp.replaceChildren();
      if (Array.isArray(lines)) {
        for (const line of lines) {
          const span = document.createElement("span");
          span.textContent = line;
          modeHelp.appendChild(span);
        }
      }
    }
  }

  function setModeStatus(text, error = false) {
    if (!modeStatus) return;
    modeStatus.textContent = text;
    modeStatus.classList.toggle("status-error", error);
  }

  async function pollSession() {
    const selected = device();
    if (!selected) return;
    if (transport !== "anyconnect" || !policyLoaded || policyBusy ||
        document.hidden || sessionInFlight) return;
    sessionInFlight = true;
    setSessionStatus("checking");
    const requestToken = ++sessionRequestToken;
    const selectedMode = anyConnectMode;
    try {
      const response = await fetch(endpoint(selected.id, "session"), {
        method: "GET",
        cache: "no-store",
        credentials: "include",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (requestToken === sessionRequestToken && device()?.id === selected.id) {
        if (data?.username !== selected.username || typeof data?.connected !== "boolean") throw new Error("Invalid session");
        sessionConnected = data?.username === selected.username &&
          data?.mode === selectedMode && data?.connected === true;
        setSessionStatus(data.connected ? "connected" : "disconnected");
      }
    } catch {
      if (requestToken === sessionRequestToken) { sessionConnected = false; setSessionStatus("failed"); }
    } finally {
      sessionInFlight = false;
      renderMode();
    }
  }

  async function loadPolicy() {
    const selected = device();
    if (!selected) return;
    const token = selectionToken;
    if (policyLoaded || policyBusy) return;
    policyBusy = true;
    policyConfirmed = false;
    setModeStatus("");
    renderMode();
    try {
      const response = await fetch(endpoint(selected.id, "policy"), {
        method: "GET",
        cache: "no-store",
        credentials: "include",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (token !== selectionToken) return;
      if (!["auto", "ru", "lv", "yt"].includes(data?.mode)) throw new Error("Invalid mode");
      anyConnectMode = data.mode;
      policyLoaded = true;
      policyConfirmed = true;
      setModeStatus("");
    } catch (error) {
      if (token !== selectionToken) return;
      console.error("AnyConnect policy load failed:", error);
      setSessionStatus("failed");
      setModeStatus(copy().failed, true);
    } finally {
      if (token === selectionToken) {
        policyBusy = false;
        renderMode();
        pollSession();
      }
    }
  }

  async function savePolicy(mode) {
    const selected = device();
    if (!selected) return;
    const token = selectionToken;
    if (policyBusy || !["auto", "ru", "lv", "yt"].includes(mode)) return;
    const previous = anyConnectMode;
    anyConnectMode = mode;
    sessionRequestToken++;
    sessionConnected = false;
    policyBusy = true;
    setSessionStatus("checking");
    policyConfirmed = false;
    setModeStatus("");
    renderMode();

    try {
      const response = await fetch(endpoint(selected.id, "policy"), {
        method: "POST",
        cache: "no-store",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ mode })
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (token !== selectionToken) return;
      if (data?.mode !== mode || data?.applied !== true) throw new Error("Mode not applied");
      anyConnectMode = data.mode;
      policyLoaded = true;
      policyConfirmed = true;
      setModeStatus("");
    } catch (error) {
      if (token !== selectionToken) return;
      console.error("AnyConnect policy save failed:", error);
      anyConnectMode = previous;
      policyConfirmed = false;
      setModeStatus(copy().failed, true);
    } finally {
      if (token === selectionToken) {
        policyBusy = false;
        renderMode();
        pollSession();
      }
    }
  }

  window.renderVpnProtocol = function () {
    overviewTitle.removeAttribute("data-i18n");
    overviewTitle.textContent = copy().protocol;
    const value = document.getElementById("vpnStatus");
    if (value) {
      value.textContent = transport === "anyconnect" ? "AnyConnect" : "IKEv2";
      value.className = "vpn-overview-status";
    }
    if (transport === "anyconnect") {
      const accountUsername = window.ocAccess?.accountUsername?.() || "";
      document.getElementById("usernameRow")?.classList.toggle("hidden", !accountUsername);
      const username = document.getElementById("vpnUsername");
      if (username) username.textContent = accountUsername;
    }
  };

  function render() {
    document.documentElement.dataset.vpnTransport = transport;
    window.renderVpnProtocol();
    setPressed();
    const riga = document.getElementById("serverRiga");
    const moscow = document.getElementById("serverMoscow");

    if (transport === "ikev2") {

      if (riga) riga.disabled = false;
      if (moscow) moscow.disabled = false;

      const restore = ikev2Server === "moscow" ? moscow : riga;
      if (restore && !restore.checked) {
        restore.checked = true;
        if (typeof updateSelectedServerAddress === "function") {
          updateSelectedServerAddress();
        }
      }

      renderMode();
      if (typeof lastVpnState !== "undefined" && lastVpnState) {
        renderVpnState(lastVpnState);
      }
      return;
    }


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
      const city = typeof t === "function" ? t("cityMoscow") : "Moscow";
      vpnServerName.textContent = city + ", " + copy().country;
    }
    if (typeof vpnServerHost !== "undefined" && vpnServerHost) {
      vpnServerHost.textContent = "";
    }
    if (typeof serverRow !== "undefined" && serverRow) {
      serverRow.classList.remove("hidden");
    }

    renderMode();
    if (policyLoaded) pollSession();
    else loadPolicy();
  }

  window.refreshAnyConnectTransport = () => {
    selectionToken++;
    sessionRequestToken++;
    policyLoaded = false;
    policyBusy = false;
    sessionConnected = false;
    setSessionStatus("checking");
    anyConnectMode = device()?.mode || "auto";
    setModeStatus("");
    render();
  };

  ikev2.addEventListener("click", () => {
    if (transport === "ikev2") return;
    transport = "ikev2";
    sessionRequestToken++;
    sessionConnected = false;
    render();
    window.dispatchEvent(new Event("vpntransportchange"));
  });

  anyConnect.addEventListener("click", () => {
    if (transport === "anyconnect") return;
    if (transport === "ikev2") {
      ikev2Server = selectedServer();
    }
    transport = "anyconnect";
    render();
    window.dispatchEvent(new Event("vpntransportchange"));
  });

  for (const button of modeButtons) {
    button.addEventListener("click", () => {
      if (transport !== "anyconnect") return;
      const mode = button.dataset.mode;
      if (mode === anyConnectMode && policyLoaded) return;
      savePolicy(mode);
    });
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      sessionRequestToken++;
      sessionConnected = false;
      renderMode();
    } else {
      pollSession();
    }
  });
  window.addEventListener("focus", pollSession);
  setInterval(pollSession, 10000);

  new MutationObserver(render).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["lang"]
  });

  render();
})();
