const LATENCY_TARGETS = {
  riga: latencyRiga,
  moscow: latencyMoscow
};

let entryPointLatencyRequest = 0;
const entryPointLatencyValues = { riga: null, moscow: null };
let entryPointLatencyMeasuring = false;

function renderLatency(target, value) {
  if (!target) return;
  target.textContent = Number.isFinite(value) && value >= 0
    ? `${Math.round(value)} ms`
    : t("connectionTestUnavailable");
}

function renderEntryPointLatencyLabels() {
  for (const key of ["riga", "moscow"]) {
    if (entryPointLatencyMeasuring) {
      if (LATENCY_TARGETS[key]) LATENCY_TARGETS[key].textContent = t("measuringConnection");
    } else {
      renderLatency(LATENCY_TARGETS[key], entryPointLatencyValues[key]);
    }
  }
}

async function measureEntryPointLatencies() {
  const request = ++entryPointLatencyRequest;
  entryPointLatencyMeasuring = true;
  renderEntryPointLatencyLabels();
  const results = await Promise.all(
    ["riga", "moscow"].map(key => resolveMeasurementTarget(key, { refresh: true }))
  );
  if (request !== entryPointLatencyRequest) return;
  entryPointLatencyMeasuring = false;
  entryPointLatencyValues.riga = results[0]?.pingT ?? null;
  entryPointLatencyValues.moscow = results[1]?.pingT ?? null;
  renderEntryPointLatencyLabels();
  if (typeof setEntryPointLatencies === "function") {
    setEntryPointLatencies(entryPointLatencyValues);
  }
}

window.addEventListener("tolf:measurement-target-resolved", event => {
  const { key, target } = event.detail;
  if (!(key in LATENCY_TARGETS)) return;
  entryPointLatencyValues[key] = target?.pingT ?? null;
  renderLatency(LATENCY_TARGETS[key], entryPointLatencyValues[key]);
});

function refreshEntryPointLatencies() {
  invalidateMeasurementTargets();
  measureEntryPointLatencies();
}

window.addEventListener("tolf:network-context-changed", refreshEntryPointLatencies);
window.addEventListener("online", refreshEntryPointLatencies);
window.addEventListener("focus", refreshEntryPointLatencies);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshEntryPointLatencies();
});
new MutationObserver(renderEntryPointLatencyLabels).observe(document.documentElement, {
  attributes: true,
  attributeFilter: ["lang"]
});

measureEntryPointLatencies();
