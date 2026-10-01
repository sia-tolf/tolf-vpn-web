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

  const POLICY_URL = `${API}/oc-test/policy`;
  let transport = "ikev2";
  let ikev2Server = null;
  let anyConnectMode = "auto";
  let policyLoaded = false;
  let policyBusy = false;
  let savedStatusTimer = null;

  const COPY = {
    en: {
      country: "Russia",
      mode: "Routing",
      saved: "Saved",
      saving: "Saving…",
      failed: "Could not save",
      loading: "Loading…",
      autoLabel: "Auto",
      auto: "RU → Moscow · rest → Riga",
      ru: "All → Moscow",
      lv: "All → Riga",
      yt: "RU + YouTube → Moscow · rest → Riga"
    },
    ru: {
      country: "Россия",
      mode: "Маршрутизация",
      saved: "Сохранено",
      saving: "Сохранение…",
      failed: "Не удалось сохранить",
      loading: "Загрузка…",
      autoLabel: "Авто",
      auto: "RU → Москва · остальное → Рига",
      ru: "Всё → Москва",
      lv: "Всё → Рига",
      yt: "RU + YouTube → Москва · остальное → Рига"
    },
    lv: {
      country: "Krievija",
      mode: "Maršrutēšana",
      saved: "Saglabāts",
      saving: "Saglabāšana…",
      failed: "Neizdevās saglabāt",
      loading: "Ielāde…",
      autoLabel: "Automātiski",
      auto: "RU → Maskava · pārējais → Rīga",
      ru: "Viss → Maskava",
      lv: "Viss → Rīga",
      yt: "RU + YouTube → Maskava · pārējais → Rīga"
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
      button.disabled = policyBusy;
    }
    if (modeHelp) {
      modeHelp.textContent = anyConnectMode ? (c[anyConnectMode] || "") : "";
    }
  }

  function setModeStatus(text, error = false) {
    if (!modeStatus) return;
    modeStatus.textContent = text;
    modeStatus.classList.toggle("status-error", error);
  }

  async function loadPolicy() {
    if (policyLoaded || policyBusy) return;
    policyBusy = true;
    setModeStatus(copy().loading);
    renderMode();
    try {
      const response = await fetch(POLICY_URL, {
        method: "GET",
        cache: "no-store",
        credentials: "omit",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (!["auto", "ru", "lv", "yt"].includes(data?.mode)) throw new Error("Invalid mode");
      anyConnectMode = data.mode;
      policyLoaded = true;
      setModeStatus("");
    } catch (error) {
      console.error("AnyConnect policy load failed:", error);
      setModeStatus(copy().failed, true);
    } finally {
      policyBusy = false;
      renderMode();
    }
  }

  async function savePolicy(mode) {
    if (policyBusy || !["auto", "ru", "lv", "yt"].includes(mode)) return;
    const previous = anyConnectMode;
    anyConnectMode = mode;
    policyBusy = true;
    setModeStatus(copy().saving);
    renderMode();

    try {
      const response = await fetch(POLICY_URL, {
        method: "POST",
        cache: "no-store",
        credentials: "omit",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ mode })
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (data?.mode !== mode || data?.applied !== true) throw new Error("Mode not applied");
      anyConnectMode = data.mode;
      policyLoaded = true;
      setModeStatus(copy().saved);
      clearTimeout(savedStatusTimer);
      savedStatusTimer = setTimeout(() => {
        if (!policyBusy) setModeStatus("");
      }, 1800);
    } catch (error) {
      console.error("AnyConnect policy save failed:", error);
      anyConnectMode = previous;
      setModeStatus(copy().failed, true);
    } finally {
      policyBusy = false;
      renderMode();
    }
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

      renderMode();
      if (typeof lastVpnState !== "undefined" && lastVpnState) {
        renderVpnState(lastVpnState);
      }
      return;
    }

    overviewTitle.textContent = "VPN · AnyConnect";

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
    loadPolicy();
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

  for (const button of modeButtons) {
    button.addEventListener("click", () => {
      if (transport !== "anyconnect") return;
      const mode = button.dataset.mode;
      if (mode === anyConnectMode && policyLoaded) return;
      savePolicy(mode);
    });
  }

  new MutationObserver(render).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["lang"]
  });

  render();
})();
