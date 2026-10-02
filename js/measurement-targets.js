// Measurement addresses describe a destination, independently of the UI protocol.
const MEASUREMENT_TARGETS = {
  riga: {
    nameKey: "cityRiga",
    servers: ["https://ikev2-riga.tolf.is:8443/"]
  },
  moscow: {
    nameKey: "cityMoscow",
    // Prefer the tunnel address instead of the excluded public VPN gateway.
    servers: [
      "https://speedtest.vpn.tolf.is:8444/",
      "https://ikev2.tolf.is:8443/"
    ]
  }
};

const measurementTargetCache = new Map();
const MEASUREMENT_CACHE_MS = 15000;

async function probeMeasurementServer(server) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2500);
  const started = performance.now();
  try {
    const response = await fetch(
      server + "empty.php?cors=true&r=" + Math.random(),
      { cache: "no-store", credentials: "omit", signal: controller.signal }
    );
    if (response.status !== 200 || await response.text() !== "") return null;
    return performance.now() - started;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

function resolveMeasurementTarget(key, { refresh = false } = {}) {
  const definition = MEASUREMENT_TARGETS[key];
  if (!definition) return Promise.resolve(null);
  const cached = measurementTargetCache.get(key);
  if (cached?.pending) return cached.promise;
  if (!refresh && cached?.result && Date.now() - cached.at < MEASUREMENT_CACHE_MS) {
    return Promise.resolve(cached.result);
  }

  const entry = { pending: true, result: null, at: 0, promise: null };
  entry.promise = (async () => {
    let result = null;
    for (const server of definition.servers) {
      const firstPing = await probeMeasurementServer(server);
      if (firstPing === null) continue;
      let pingT = firstPing;
      for (let sample = 1; sample < 3; sample++) {
        const ping = await probeMeasurementServer(server);
        if (ping !== null) pingT = Math.min(pingT, ping);
      }
      result = { nameKey: definition.nameKey, server, pingT };
      break;
    }
    entry.pending = false;
    entry.result = result;
    entry.at = Date.now();
    if (measurementTargetCache.get(key) === entry) {
      window.dispatchEvent(new CustomEvent("tolf:measurement-target-resolved", {
        detail: { key, target: result }
      }));
    }
    return result;
  })();
  measurementTargetCache.set(key, entry);
  return entry.promise;
}

function invalidateMeasurementTargets() {
  measurementTargetCache.clear();
}
