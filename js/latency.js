const LATENCY_TARGETS = {
  riga: latencyRiga,
  moscow: latencyMoscow
};

let entryPointLatencyRequest = 0;

function renderLatency(target, value) {
  if (!target) return;

  if (Number.isFinite(value) && value >= 0) {
    target.textContent = `${Math.round(value)} ms`;
  } else {
    target.textContent = "—";
  }
}

function measureEntryPointLatencies() {
  const request = ++entryPointLatencyRequest;
  const isAnyConnect = window.getVpnTransport?.() === "anyconnect";
  if (typeof Speedtest !== "function") {
    renderLatency(LATENCY_TARGETS.riga, -1);
    renderLatency(LATENCY_TARGETS.moscow, -1);
    return;
  }

  LATENCY_TARGETS.riga.textContent = "Measuring…";
  LATENCY_TARGETS.moscow.textContent = "Measuring…";

  const riga = {
    name: "Riga",
    server: "https://ikev2-riga.tolf.is:8443/",
    dlURL: "garbage.php",
    ulURL: "empty.php",
    pingURL: "empty.php",
    getIpURL: "getIP.php"
  };

  const moscow = {
    name: "Moscow",
    server: isAnyConnect
      ? "https://speedtest.vpn.tolf.is:8444/"
      : "https://ikev2.tolf.is:8443/",
    dlURL: "garbage.php",
    ulURL: "empty.php",
    pingURL: "empty.php",
    getIpURL: "getIP.php"
  };

  try {
    const speedtest = new Speedtest();

    speedtest.addTestPoints([riga, moscow]);

    speedtest.selectServer(() => {
      if (request !== entryPointLatencyRequest) return;
      renderLatency(LATENCY_TARGETS.riga, riga.pingT);
      renderLatency(LATENCY_TARGETS.moscow, moscow.pingT);

      if (typeof setEntryPointLatencies === "function") {
        setEntryPointLatencies({
          riga: riga.pingT,
          moscow: moscow.pingT
        });
      }
    });
  } catch (error) {
    console.error("Entry point latency test failed:", error);
    renderLatency(LATENCY_TARGETS.riga, -1);
    renderLatency(LATENCY_TARGETS.moscow, -1);
  }
}

measureEntryPointLatencies();

if (
  typeof window !== "undefined"
  && typeof window.addEventListener === "function"
) {
  window.addEventListener(
    "tolf:network-context-changed",
    measureEntryPointLatencies
  );
  window.addEventListener("vpntransportchange", measureEntryPointLatencies);
}
