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
  const endpoint = (id, action) => API + '/oc/access/devices/' + encodeURIComponent(id) + '/' + action + (action === 'policy' ? '?ingress=' + encodeURIComponent(window.ocAccess?.ingress?.().id || 'moscow') : '');
  let selectionToken = 0;
  const readChoice = key => { try { return sessionStorage.getItem(key); } catch { return null; } };
  const saveChoice = (key,value) => { try { sessionStorage.setItem(key,value); } catch {} };
  let transport = "";
  saveChoice("tolfTransport", "");
  window.getVpnTransport = () => transport;
  let ikev2Server = readChoice("tolfIkev2Server");
  let anyConnectMode = "auto";
  let supportedModes = ["auto","ru","lv","yt"];
  let policyLoaded = false;
  let policyBusy = false;
  let savedStatusTimer = null;
  let policyConfirmed = false;
  let sessionConnected = false;
  let sessionInFlight = false;
  let sessionRequestToken = 0;
  let sessionStatus = "checking";
  let sessionNodes = null;
  window.getAnyConnectSessionStatus = () => ({id: device()?.id, status: sessionStatus, nodes: sessionNodes});
  function setSessionStatus(status) {
    sessionStatus = status;
    window.updateAnyConnectSessionStatus?.();
  }

  const COPY = {
    en: {
      country: "Russia",
      rigaCountry: 'Latvia',
      protocol: "Protocol",
      mode: "Route",
      saved: "Applied",
      saving: "Saving…",
      failed: "Could not save",
      loading: "Loading…",
      pending: 'Waiting for routing to apply',
      autoLabel: "Auto",
      auto: ["RU → Moscow", "rest → Riga"],
      ru: ["All traffic", "→ Moscow"],
      lv: ["All traffic", "→ Riga"],
      yt: ["RU + YouTube → Moscow", "rest → Riga"]
    },
    ru: {
      country: "Россия",
      rigaCountry: 'Латвия',
      protocol: "Протокол",
      mode: "Маршрут",
      saved: "Применено",
      saving: "Сохранение…",
      failed: "Не удалось сохранить",
      loading: "Загрузка…",
      pending: 'Ожидает применения маршрутизации',
      autoLabel: "Авто",
      auto: ["RU → Москва", "остальное → Рига"],
      ru: ["Весь трафик", "→ Москва"],
      lv: ["Весь трафик", "→ Рига"],
      yt: ["RU + YouTube → Москва", "остальное → Рига"]
    },
    lv: {
      country: "Krievija",
      rigaCountry: 'Latvija',
      protocol: "Protokols",
      mode: "Maršruts",
      saved: "Piemērots",
      saving: "Saglabāšana…",
      failed: "Neizdevās saglabāt",
      loading: "Ielāde…",
      pending: 'Gaida maršrutēšanas piemērošanu',
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
    const us = {ru:['Весь трафик','→ Нью-Йорк'],en:['All traffic','→ New York'],lv:['Visa datplūsma','→ Ņujorka']}[lang()];
    const c = {...COPY[lang()],us};
    if (window.ocAccess?.ingress?.().id !== 'us') return c;
    const rest = {ru:'остальное → Нью-Йорк',en:'rest → New York',lv:'pārējais → Ņujorka'}[lang()];
    return {...c, auto:[c.auto[0],rest], yt:[c.yt[0],rest]};
  }

  function selectedServer() {
    return Array.from(typeof serverInputs !== "undefined" ? serverInputs : [])
      .find(input => input.checked)?.value || null;
  }

  function setPressed() {
    const isIkev2 = transport === "ikev2";
    ikev2.classList.toggle("active", isIkev2);
    anyConnect.classList.toggle("active", transport === "anyconnect");
    ikev2.setAttribute("aria-pressed", String(isIkev2));
    anyConnect.setAttribute("aria-pressed", String(transport === "anyconnect"));
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
      const description = (c[button.dataset.mode] || []).join("\n");
      button.setAttribute("data-tooltip", description);
      button.setAttribute("aria-description", description);
      if (button.dataset.mode === 'us') button.classList.toggle('hidden', window.ocAccess?.ingress?.().id !== 'moscow' || !supportedModes.includes('us'));
      button.disabled = policyBusy || !device();
    }
    const controls = document.getElementById("anyConnectModeSelector");
    controls?.classList.toggle('has-us', window.ocAccess?.ingress?.().id === 'moscow' && supportedModes.includes('us'));
    controls?.classList.toggle("policy-confirmed",
      policyLoaded && !policyBusy && sessionConnected);

    if (modeHelp) {
      modeHelp.replaceChildren();
      modeHelp.hidden = true;
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
    const requestToken = ++sessionRequestToken;
    let selectedMode = anyConnectMode;
    try {
      if (!policyConfirmed) {
        const response = await fetch(endpoint(selected.id, 'policy'), {method:'GET',cache:'no-store',credentials:'include',headers:{Accept:'application/json'}});
        if (!response.ok) throw new Error('Policy unavailable');
        const data = await response.json();
        if (requestToken !== sessionRequestToken || device()?.id !== selected.id) return;
        if (data.username !== selected.username || !['auto','ru','lv','us','yt'].includes(data.mode)) throw new Error('Invalid policy');
        anyConnectMode = data.mode; selectedMode = data.mode; supportedModes = data.supportedModes || supportedModes; policyConfirmed = data.applied === true;
        setModeStatus(policyConfirmed ? copy().saved : copy().pending);
        if (!policyConfirmed) { sessionConnected = false; return; }
      }
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
          (data?.mode === selectedMode || selectedMode === "us") && data?.connected === true;
        sessionNodes = data.nodes || null;
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
    setModeStatus(copy().loading);
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
      if (!["auto", "ru", "lv", "us", "yt"].includes(data?.mode)) throw new Error("Invalid mode");
      anyConnectMode = data.mode;
      supportedModes = Array.isArray(data.supportedModes) ? data.supportedModes : supportedModes;
      policyLoaded = true;
      policyConfirmed = data.applied === true;
      setModeStatus(policyConfirmed ? copy().saved : copy().pending);
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
    if (policyBusy || !["auto", "ru", "lv", "us", "yt"].includes(mode)) return;
    const previous = anyConnectMode;
    anyConnectMode = mode;
    sessionRequestToken++;
    sessionConnected = false;
    policyBusy = true;
    setSessionStatus("checking");
    policyConfirmed = false;
    setModeStatus(copy().saving);
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
      setModeStatus(copy().saved);
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
      value.textContent = transport === "anyconnect" ? "AnyConnect" : transport === "ikev2" ? "IKEv2" : "—";
      value.className = "vpn-overview-status";
    }
    if (transport === "anyconnect") {
      const accountUsername = window.ocAccess?.accountUsername?.() || "";
      document.getElementById("usernameRow")?.classList.toggle("hidden", !accountUsername);
      const username = document.getElementById("vpnUsername");
      if (username) username.textContent = accountUsername;
      const point = window.ocAccess?.ingress?.().id || 'moscow';
      const points = window.ocAccess?.ingresses?.() || [{id:'moscow'}];
      for (const name of ['riga','moscow']) {
        const input = document.getElementById(name === 'riga' ? 'serverRiga' : 'serverMoscow');
        if (input) { input.disabled = !points.some(value => value.id === name); input.checked = point === name; }
      }
      if (typeof vpnServerName !== 'undefined' && vpnServerName) {
        const city = typeof t === 'function' ? t(point === 'riga' ? 'cityRiga' : 'cityMoscow') : point === 'riga' ? 'Riga' : 'Moscow';
        vpnServerName.textContent = point === 'us' ? ({ru:'Нью-Йорк',en:'New York',lv:'Ņujorka'}[lang()]) : city + ', ' + (point === 'riga' ? copy().rigaCountry : copy().country);
      }
      if (typeof vpnServerHost !== 'undefined' && vpnServerHost) vpnServerHost.textContent = '';
      if (typeof serverRow !== 'undefined' && serverRow) serverRow.classList.remove('hidden');
    }
  };

  function render() {
    document.documentElement.dataset.vpnTransport = transport;
    window.renderVpnProtocol();
    setPressed();
    if (!transport) return;
    const riga = document.getElementById("serverRiga");
    const moscow = document.getElementById("serverMoscow");

    if (transport === "ikev2") {

      if (riga) riga.disabled = false;
      if (moscow) moscow.disabled = false;

      const ny = document.getElementById("serverNewYork");
      if (ny) ny.disabled = !window.tolfMobileIkev2Ready;
      const restore = ikev2Server === "us" && window.tolfMobileIkev2Ready ? ny : ikev2Server === "moscow" ? moscow : riga;
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


    if (typeof updateSelectedServerAddress === "function") {
      updateSelectedServerAddress();
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
    sessionNodes = null;
    setSessionStatus("checking");
    anyConnectMode = device()?.mode || "auto";
    setModeStatus("");
    render();
    window.dispatchEvent(new Event('tolf:ingress-changed'));
  };

  window.refreshAnyConnectIngress = () => {
    if (transport !== 'anyconnect') return;
    selectionToken++; sessionRequestToken++;
    policyLoaded = false; policyBusy = false; policyConfirmed = false;
    supportedModes = ['auto','ru','lv','yt'];
    anyConnectMode = device()?.mode || 'auto';
    render();
    window.dispatchEvent(new Event('vpntransportchange'));
  };
  for (const input of typeof serverInputs !== 'undefined' ? serverInputs : []) {
    input.addEventListener('change', () => {
      if (transport === 'anyconnect') window.ocAccess?.selectIngress?.(input.value);
      else { ikev2Server = input.value; saveChoice("tolfIkev2Server", input.value); }
    });
  }

  ikev2.addEventListener("click", () => {
    if (transport === "ikev2") return;
    transport = "ikev2";
    saveChoice("tolfTransport", transport);
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
    saveChoice("tolfTransport", transport);
    render();
    window.dispatchEvent(new Event("vpntransportchange"));
  });

  for (const button of modeButtons) {
    // iPad can report a touch-first device even with a mouse or trackpad.
    button.addEventListener("pointerenter", event => {
      if (event.pointerType !== "touch") button.classList.add("tooltip-hover");
    });
    button.addEventListener("pointerleave", () => button.classList.remove("tooltip-hover"));
    button.addEventListener("mouseenter", () => button.classList.add("tooltip-hover"));
    button.addEventListener("mouseleave", () => button.classList.remove("tooltip-hover"));
    button.addEventListener("click", () => {
      if (transport !== "anyconnect") return;
      const mode = button.dataset.mode;
      if (mode === anyConnectMode && policyLoaded) {
        const visible = button.classList.contains("tooltip-open");
        for (const item of modeButtons) item.classList.remove("tooltip-open");
        button.classList.toggle("tooltip-open", !visible);
        return;
      }
      for (const item of modeButtons) item.classList.remove("tooltip-open");
      savePolicy(mode);
    });
  }

  document.addEventListener("pointerdown", event => {
    if (!modeButtons.some(button => button === event.target || button.contains?.(event.target)))
      for (const button of modeButtons) button.classList.remove("tooltip-open");
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") for (const button of modeButtons) button.classList.remove("tooltip-open");
  });

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
