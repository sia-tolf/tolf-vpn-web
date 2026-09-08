const LOCATION_API = API;
const entryPointNote = document.getElementById("entryPointNote");

const LATENCY_OVERRIDE_THRESHOLD_MS = 60;

let geographicEntryPoint = null;
let recommendedEntryPoint = null;
let entryPointChangedManually = false;
let recommendationRequestNumber = 0;

let measuredLatencies = {
  riga: null,
  moscow: null
};

function latencyAvailable(value) {
  return Number.isFinite(value) && value >= 0;
}

function calculateRecommendedEntryPoint() {
  if (
    geographicEntryPoint !== "moscow"
    && geographicEntryPoint !== "riga"
  ) {
    return null;
  }

  const riga = measuredLatencies.riga;
  const moscow = measuredLatencies.moscow;

  const rigaAvailable = latencyAvailable(riga);
  const moscowAvailable = latencyAvailable(moscow);

  if (geographicEntryPoint === "moscow") {
    if (!moscowAvailable && rigaAvailable) {
      return "riga";
    }

    if (
      moscowAvailable
      && rigaAvailable
      && moscow >= riga + LATENCY_OVERRIDE_THRESHOLD_MS
    ) {
      return "riga";
    }

    return "moscow";
  }

  if (!rigaAvailable && moscowAvailable) {
    return "moscow";
  }

  if (
    rigaAvailable
    && moscowAvailable
    && riga >= moscow + LATENCY_OVERRIDE_THRESHOLD_MS
  ) {
    return "moscow";
  }

  return "riga";
}

function updateRecommendedEntryPoint() {
  const nextRecommendation = calculateRecommendedEntryPoint();

  if (
    nextRecommendation !== "moscow"
    && nextRecommendation !== "riga"
  ) {
    return;
  }

  recommendedEntryPoint = nextRecommendation;

  renderEntryPointRecommendation();
  selectRecommendedEntryPoint();
}

function setEntryPointLatencies(latencies) {
  measuredLatencies = {
    riga: latencyAvailable(latencies?.riga)
      ? latencies.riga
      : null,
    moscow: latencyAvailable(latencies?.moscow)
      ? latencies.moscow
      : null
  };

  updateRecommendedEntryPoint();
}

function selectRecommendedEntryPoint() {
  if (
    recommendedEntryPoint !== "moscow"
    && recommendedEntryPoint !== "riga"
  ) {
    return;
  }

  renderEntryPointRecommendation();

  if (entryPointChangedManually) {
    return;
  }

  const target = document.getElementById(
    recommendedEntryPoint === "moscow"
      ? "serverMoscow"
      : "serverRiga"
  );

  if (!target || target.disabled) {
    return;
  }

  if (target.checked) {
    return;
  }

  for (const input of serverInputs) {
    input.checked = input === target;
  }

  setInstallLink(null);

  vpnMessage.textContent = "";
  vpnMessage.className = "message";

  updateSelectedServerAddress();

  if (lastVpnState) {
    renderVpnState(lastVpnState);
  }
}

function renderEntryPointRecommendation() {
  if (!entryPointNote) {
    return;
  }

  const key = recommendedEntryPoint === "moscow"
    ? "entryPointRecommendationMoscow"
    : recommendedEntryPoint === "riga"
      ? "entryPointRecommendationRiga"
      : null;

  if (!key) {
    entryPointNote.textContent = "";
    entryPointNote.className = "entry-point-note hidden";
    return;
  }

  entryPointNote.textContent = t(key);
  entryPointNote.className = "entry-point-note";
}

async function loadEntryPointRecommendation() {
  try {
    const requestNumber = ++recommendationRequestNumber;

    const response = await fetch(
      `${LOCATION_API}/entry-point-recommendation?request=${Date.now()}-${requestNumber}`,
      {
        method: "GET",
        cache: "no-store",
        credentials: "omit",
        headers: {
          Accept: "application/json"
        }
      }
    );

    if (!response.ok) {
      return;
    }

    const data = await response.json();

    if (requestNumber !== recommendationRequestNumber) {
      return;
    }

    if (
      data.entryPoint !== "moscow"
      && data.entryPoint !== "riga"
    ) {
      return;
    }

    const previousGeographicEntryPoint = geographicEntryPoint;

    geographicEntryPoint = data.entryPoint;

    const geographicEntryPointChanged =
      previousGeographicEntryPoint !== null
      && previousGeographicEntryPoint !== geographicEntryPoint;

    if (geographicEntryPointChanged) {
      measuredLatencies = {
        riga: null,
        moscow: null
      };
    }

    updateRecommendedEntryPoint();

    if (
      geographicEntryPointChanged
      && typeof window !== "undefined"
    ) {
      window.dispatchEvent(
        new Event("tolf:network-context-changed")
      );
    }
  } catch {
    // Recommendation is optional.
    // VPN controls remain available.
  }
}

for (const input of serverInputs) {
  input.addEventListener("change", event => {
    if (event.isTrusted) {
      entryPointChangedManually = true;
    }
  });
}

languageEn.addEventListener(
  "click",
  renderEntryPointRecommendation
);

languageRu.addEventListener(
  "click",
  renderEntryPointRecommendation
);

renderEntryPointRecommendation();
loadEntryPointRecommendation();

if (typeof setTimeout === "function") {
  setTimeout(
    loadEntryPointRecommendation,
    1500
  );
}

if (typeof setInterval === "function") {
  setInterval(() => {
    if (
      typeof document === "undefined"
      || document.visibilityState !== "hidden"
    ) {
      loadEntryPointRecommendation();
    }
  }, 10000);
}

if (
  typeof window !== "undefined"
  && typeof window.addEventListener === "function"
) {
  window.addEventListener(
    "focus",
    loadEntryPointRecommendation
  );

  window.addEventListener(
    "online",
    loadEntryPointRecommendation
  );

  window.addEventListener("pageshow", event => {
    if (event.persisted) {
      loadEntryPointRecommendation();
    }
  });
}

if (
  typeof document !== "undefined"
  && typeof document.addEventListener === "function"
) {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "hidden") {
      loadEntryPointRecommendation();
    }
  });
}
