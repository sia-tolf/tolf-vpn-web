const LOCATION_API = "https://location.tolf.is";
const entryPointNote = document.getElementById("entryPointNote");
let recommendedEntryPoint = null;
let entryPointChangedManually = false;
let recommendationRequestNumber = 0;

function selectRecommendedEntryPoint() {
  if (recommendedEntryPoint !== "moscow" && recommendedEntryPoint !== "riga") return;

  renderEntryPointRecommendation();
  if (entryPointChangedManually) return;

  const target = document.getElementById(
    recommendedEntryPoint === "moscow" ? "serverMoscow" : "serverRiga"
  );
  if (!target || target.disabled) return;
  if (target.checked) return;

  for (const input of serverInputs) {
    input.checked = input === target;
  }

  setInstallLink(null);
  vpnMessage.textContent = "";
  vpnMessage.className = "message";
  updateSelectedServerAddress();
  if (lastVpnState) renderVpnState(lastVpnState);
}

function renderEntryPointRecommendation() {
  if (!entryPointNote) return;

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
      `${LOCATION_API}/recommendation?request=${Date.now()}-${requestNumber}`,
      {
        method: "GET",
        cache: "no-store",
        credentials: "omit",
        headers: { Accept: "application/json" }
      }
    );

    if (!response.ok) return;

    const data = await response.json();
    if (requestNumber !== recommendationRequestNumber) return;
    if (data.entryPoint !== "moscow" && data.entryPoint !== "riga") return;

    const recommendationChanged =
      recommendedEntryPoint !== null && recommendedEntryPoint !== data.entryPoint;

    recommendedEntryPoint = data.entryPoint;

    if (recommendationChanged) {
      entryPointChangedManually = false;
    }

    renderEntryPointRecommendation();
    selectRecommendedEntryPoint();
  } catch {
    // The recommendation is optional. VPN controls remain available.
  }
}

for (const input of serverInputs) {
  input.addEventListener("change", event => {
    if (event.isTrusted) entryPointChangedManually = true;
  });
}

languageEn.addEventListener("click", renderEntryPointRecommendation);
languageRu.addEventListener("click", renderEntryPointRecommendation);

renderEntryPointRecommendation();
loadEntryPointRecommendation();

if (typeof setTimeout === "function") {
  setTimeout(loadEntryPointRecommendation, 1500);
}

if (typeof setInterval === "function") {
  setInterval(() => {
    if (typeof document === "undefined" || document.visibilityState !== "hidden") {
      loadEntryPointRecommendation();
    }
  }, 10000);
}

if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
  window.addEventListener("focus", loadEntryPointRecommendation);
  window.addEventListener("online", loadEntryPointRecommendation);

  window.addEventListener("pageshow", event => {
    if (event.persisted) {
      loadEntryPointRecommendation();
    }
  });
}

if (typeof document !== "undefined" && typeof document.addEventListener === "function") {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "hidden") {
      loadEntryPointRecommendation();
    }
  });
}
