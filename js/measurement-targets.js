// Measurement addresses describe a destination, independently of the UI protocol.
const MEASUREMENT_TARGETS = {
  us: {
    nameKey: "cityNewYork",
    vpnReady: true,
    servers: ["https://ikev2-us.tolf.is:8443/"],
    directServers: ["https://ikev2-us.tolf.is:8443/"],
    connectionServers: ["https://speedtest-us.vpn.tolf.is:8444/"]
  },
  riga: {
    nameKey: "cityRiga",
    servers: ["https://ikev2-riga.tolf.is:8443/"],
    directServers: ["https://ikev2-riga.tolf.is:8443/"],
    connectionServers: ["https://speedtest-riga.vpn.tolf.is:8444/"]
  },
  moscow: {
    nameKey: "cityMoscow",
    directServers: ["https://ikev2.tolf.is:8443/"],
    connectionServers: ["https://speedtest.vpn.tolf.is:8444/"],
    // Prefer the tunnel address instead of the excluded public VPN gateway.
    servers: [
      "https://speedtest.vpn.tolf.is:8444/",
      "https://ikev2.tolf.is:8443/"
    ]
  }
};

const measurementTargetCache = new Map();
const MEASUREMENT_CACHE_MS = 15000;

async function probeMeasurementServer(server, timeoutMs = 2500) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
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

function resolveMeasurementTarget(key, { refresh = false, purpose = "entry" } = {}) {
  const definition = MEASUREMENT_TARGETS[key];
  if (!definition) return Promise.resolve(null);
  // Entry latency and VPN throughput must never reuse each other's target.
  const cacheKey = key + ":" + purpose;
  const vpnOnly = purpose === "connection" && !!definition.connectionServers;
  const candidates = vpnOnly ? definition.connectionServers
    : purpose === "direct" ? definition.directServers : definition.servers;
  const cached = measurementTargetCache.get(cacheKey);
  if (cached?.pending) return cached.promise;
  if (!refresh && cached?.result && Date.now() - cached.at < MEASUREMENT_CACHE_MS) {
    return Promise.resolve(cached.result);
  }

  const entry = { pending: true, result: null, at: 0, promise: null };
  entry.promise = (async () => {
    let result = null;
    for (const server of candidates) {
      // A user-initiated VPN probe can wait for the browser network permission.
      const firstPing = await probeMeasurementServer(server, vpnOnly ? 20000 : 2500);
      if (firstPing === null) continue;
      let pingT = firstPing;
      for (let sample = 1; sample < 3; sample++) {
        const ping = await probeMeasurementServer(server);
        if (ping !== null) pingT = Math.min(pingT, ping);
      }
      result = { nameKey: definition.nameKey, server, pingT, viaVpn: vpnOnly };
      break;
    }
    entry.pending = false;
    entry.result = result;
    entry.at = Date.now();
    if (purpose === "entry" && measurementTargetCache.get(cacheKey) === entry) {
      window.dispatchEvent(new CustomEvent("tolf:measurement-target-resolved", {
        detail: { key, target: result }
      }));
    }
    return result;
  })();
  measurementTargetCache.set(cacheKey, entry);
  return entry.promise;
}

function invalidateMeasurementTargets() {
  measurementTargetCache.clear();
}


// Only classify the request path; do not store or display the visitor address.
const TOLF_MEASUREMENT_EGRESS = new Set([
  "188.214.39.114", "92.243.66.32", "92.243.66.204", "162.252.174.201"
]);
function measurementSourcePath(value) {
  if (typeof value !== "string") return "unknown";
  const address = value.trim().replace(/^::ffff:/i, "");
  if (!/^\d{1,3}(?:\.\d{1,3}){3}$/.test(address)) return "unknown";
  const octets = address.split(".").map(Number);
  if (octets.some(x => x > 255)) return "unknown";
  if (TOLF_MEASUREMENT_EGRESS.has(octets.join("."))) return "vpn";
  const [a,b] = octets;
  if (a === 10 || a === 172 && b >= 16 && b <= 31 || a === 192 && b === 168 || a === 100 && b >= 64 && b <= 127) return "vpn";
  if (a === 0 || a === 127 || a >= 224 || a === 169 && b === 254) return "unknown";
  return "direct";
}

async function verifyDirectMeasurementPath(server) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(server + "getIP.php?cors=true&r=" + Math.random(), {
      cache: "no-store", credentials: "omit", signal: controller.signal
    });
    if (response.status !== 200) return "unknown";
    const data = await response.json();
    return measurementSourcePath(data?.processedString);
  } catch {
    return "unknown";
  } finally {
    clearTimeout(timeout);
  }
}
