const LATENCY_ENDPOINTS = {
  riga: "https://ikev2-riga.tolf.is/ping",
  moscow: "https://ikev2.tolf.is:8443/cgi-bin/ping"
};

const LATENCY_TARGETS = {
  riga: latencyRiga,
  moscow: latencyMoscow
};

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

async function measureRequest(url) {
  const marker = `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}-${Math.random()}`;

  performance.clearResourceTimings();

  const response = await fetch(marker, {
    method: "GET",
    mode: "cors",
    cache: "no-store",
    credentials: "omit"
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  await response.text();

  const entries = performance.getEntriesByName(marker);
  const timing = entries[entries.length - 1];

  if (
    timing
    && timing.requestStart > 0
    && timing.responseStart > timing.requestStart
  ) {
    return timing.responseStart - timing.requestStart;
  }

  throw new Error("Resource Timing unavailable");
}

async function measureEntryPointLatency(serverKey) {
  const endpoint = LATENCY_ENDPOINTS[serverKey];
  const target = LATENCY_TARGETS[serverKey];

  if (!endpoint || !target) return;

  target.textContent = "Measuring…";

  try {
    const samples = [];

    for (let i = 0; i < 5; i += 1) {
      const ms = await measureRequest(endpoint);

      if (i > 0) {
        samples.push(ms);
      }
    }

    target.textContent = `${Math.round(median(samples))} ms`;
  } catch {
    target.textContent = "—";
  }
}

function measureEntryPointLatencies() {
  void measureEntryPointLatency("riga");
  void measureEntryPointLatency("moscow");
}

measureEntryPointLatencies();
