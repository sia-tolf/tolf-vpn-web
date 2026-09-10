const CONNECTION_TEST_SERVERS = {
  riga: {
    nameKey: "cityRiga",
    server: "https://ikev2-riga.tolf.is:8443/"
  },
  moscow: {
    nameKey: "cityMoscow",
    server: "https://ikev2.tolf.is:8443/"
  }
};

let activeConnectionTest = null;
let activeConnectionTestServer = null;
let connectionTestWatchdog = null;

function connectionMetric(value, unit, decimals = 1) {
  const number = Number.parseFloat(value);
  return Number.isFinite(number) && number >= 0
    ? `${number.toFixed(decimals)} ${unit}`
    : "—";
}

function setConnectionTestButtonLabel(key) {
  const label = connectionTestButton?.querySelector("span");
  if (label) label.textContent = t(key);
}

function renderConnectionTestTarget() {
  if (!connectionTestTitle) return;

  const serverKey = activeConnectionTestServer || getSelectedServerKey();
  const server = CONNECTION_TEST_SERVERS[serverKey];

  connectionTestTitle.textContent = t("connectionTo", {
    city: t(server?.nameKey || "cityRiga")
  });
}

function resetConnectionTestResults() {
  for (const target of [
    connectionTestLatency,
    connectionTestJitter,
    connectionTestDownload,
    connectionTestUpload
  ]) {
    if (target) target.textContent = "—";
  }

  if (connectionTestStatus) {
    connectionTestStatus.textContent = t("connectionTestReady");
    connectionTestStatus.className = "vpn-overview-updated";
  }
}

function setConnectionTestRunning(running) {
  if (!connectionTestButton) return;

  connectionTestButton.disabled = running;
  connectionTestButton.setAttribute("aria-busy", String(running));
  setConnectionTestButtonLabel(
    running ? "measuringConnection" : "measureConnection"
  );
}

function updateConnectionTestResults(data) {
  if (connectionTestLatency) {
    connectionTestLatency.textContent = connectionMetric(
      data?.pingStatus,
      "ms"
    );
  }

  if (connectionTestJitter) {
    connectionTestJitter.textContent = connectionMetric(
      data?.jitterStatus,
      "ms"
    );
  }

  if (connectionTestDownload) {
    connectionTestDownload.textContent = connectionMetric(
      data?.dlStatus,
      "Mbps"
    );
  }

  if (connectionTestUpload) {
    connectionTestUpload.textContent = connectionMetric(
      data?.ulStatus,
      "Mbps"
    );
  }
}

function connectionTestHasResult() {
  return [
    connectionTestLatency,
    connectionTestDownload,
    connectionTestUpload
  ].every(target => target && Number.isFinite(Number.parseFloat(target.textContent)));
}

function finishConnectionTest(aborted) {
  const completed = !aborted && connectionTestHasResult();
  if (activeConnectionTest) {
    clearInterval(activeConnectionTest.updater);
    activeConnectionTest.worker?.terminate();
  }

  if (connectionTestStatus) {
    connectionTestStatus.textContent = t(
      completed ? "connectionTestComplete" : "connectionTestFailed"
    );
    connectionTestStatus.className = completed
      ? "vpn-overview-updated status-active"
      : "vpn-overview-updated status-error";
  }

  activeConnectionTest = null;
  clearTimeout(connectionTestWatchdog);
  setConnectionTestRunning(false);
  renderConnectionTestTarget();
}

function startConnectionTest() {
  if (activeConnectionTest || typeof Speedtest !== "function") {
    if (typeof Speedtest !== "function" && connectionTestStatus) {
      connectionTestStatus.textContent = t("connectionTestFailed");
      connectionTestStatus.className = "vpn-overview-updated status-error";
    }
    return;
  }

  const serverKey = getSelectedServerKey();
  const target = CONNECTION_TEST_SERVERS[serverKey];

  if (!target) return;

  resetConnectionTestResults();
  activeConnectionTestServer = serverKey;
  renderConnectionTestTarget();

  if (connectionTestStatus) {
    connectionTestStatus.textContent = t("measuringConnection");
    connectionTestStatus.className = "vpn-overview-updated";
  }

  setConnectionTestRunning(true);

  try {
    const speedtest = new Speedtest();
    activeConnectionTest = speedtest;

    speedtest.setParameter("test_order", "P_D_U");
    speedtest.setParameter("count_ping", 10);
    speedtest.setParameter("time_dl_max", 15);
    speedtest.setParameter("time_ul_max", 15);
    speedtest.setParameter("time_auto", false);
    // Do not include a pre-warmup request in a later accounting window.
    speedtest.setParameter("time_ulGraceTime", 0);
    speedtest.setParameter("xhr_dlMultistream", 8);
    speedtest.setParameter("xhr_ulMultistream", 4);
    speedtest.setParameter("xhr_ul_blob_megabytes", 4);
    speedtest.setParameter("telemetry_level", 0);
    speedtest.setParameter("overheadCompensationFactor", 1);
    speedtest.setParameter("xhr_ignoreErrors", 0);
    // Use response-confirmed uploads on every browser, including Safari.
    speedtest.setParameter("forceIE11Workaround", true);

    speedtest.setSelectedServer({
      name: t(target.nameKey),
      server: target.server,
      dlURL: "garbage.php",
      ulURL: "empty.php",
      pingURL: "empty.php",
      getIpURL: "getIP.php"
    });

    speedtest.onupdate = updateConnectionTestResults;
    speedtest.onend = finishConnectionTest;
    speedtest.start();
    connectionTestWatchdog = setTimeout(() => {
      if (activeConnectionTest !== speedtest) return;
      speedtest.abort();
      resetConnectionTestResults();
      finishConnectionTest(true);
    }, 90000);
  } catch (error) {
    console.error("Connection test failed:", error);
    finishConnectionTest(true);
  }
}

connectionTestButton?.addEventListener("click", startConnectionTest);

for (const input of serverInputs) {
  input.addEventListener("change", () => {
    if (!activeConnectionTest) {
      activeConnectionTestServer = null;
      resetConnectionTestResults();
      renderConnectionTestTarget();
    }
  });
}

if (connectionTestStatus) {
  connectionTestStatus.setAttribute("aria-live", "polite");
}

resetConnectionTestResults();
renderConnectionTestTarget();
