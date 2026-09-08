const LATENCY_ENDPOINTS = {
  riga: "https://ikev2-riga.tolf.is/ping",
  moscow: "https://install-ru.tolf.is/cgi-bin/ping"
};

const LATENCY_TARGETS = {
  riga: latencyRiga,
  moscow: latencyMoscow
};

async function measureRequest(url) {
  const started = performance.now();

  const response = await fetch(url, {
    method: "GET",
    mode: "cors",
    cache: "no-store",
    credentials: "omit"
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  await response.text();

  return performance.now() - started;
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

async function measureEntryPointLatency(serverKey) {
  const endpoint = LATENCY_ENDPOINTS[serverKey];
  const target = LATENCY_TARGETS[serverKey];

  if (!endpoint || !target) return;

  target.textContent = "Measuring…";

  try {
    const samples = [];

    for (let i = 0; i < 4; i += 1) {
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
