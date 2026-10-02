let activeConnectionTest = null;
let activeConnectionTestServer = null;
let connectionTestWatchdog = null;
let connectionTestPreparing = false;
let connectionTestRequest = 0;
let connectionTestStatusKey = "connectionTestReady";

function getConnectionTestServerKey() {
  return getSelectedServerKey();
}

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

  const serverKey = activeConnectionTestServer || getConnectionTestServerKey();
  const server = MEASUREMENT_TARGETS[serverKey];

  connectionTestTitle.textContent = t("connectionTo", {
    city: t(server?.nameKey || "cityRiga")
  });
  if (connectionTestStatus) connectionTestStatus.textContent = t(connectionTestStatusKey);
  setConnectionTestButtonLabel(
    activeConnectionTest || connectionTestPreparing ? "measuringConnection" : "measureConnection"
  );
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
    connectionTestStatusKey = "connectionTestReady";
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
    connectionTestStatusKey = completed ? "connectionTestComplete" : "connectionTestFailed";
    connectionTestStatus.textContent = t(connectionTestStatusKey);
    connectionTestStatus.className = completed
      ? "vpn-overview-updated status-active"
      : "vpn-overview-updated status-error";
  }

  activeConnectionTest = null;
  clearTimeout(connectionTestWatchdog);
  setConnectionTestRunning(false);
  renderConnectionTestTarget();
}

async function startConnectionTest() {
  if (activeConnectionTest || connectionTestPreparing || typeof Speedtest !== "function") {
    if (typeof Speedtest !== "function" && connectionTestStatus) {
      connectionTestStatusKey = "connectionTestFailed";
      connectionTestStatus.textContent = t("connectionTestFailed");
      connectionTestStatus.className = "vpn-overview-updated status-error";
    }
    return;
  }

  const serverKey = getConnectionTestServerKey();
  if (!MEASUREMENT_TARGETS[serverKey]) return;
  const request = ++connectionTestRequest;

  resetConnectionTestResults();
  activeConnectionTestServer = serverKey;
  renderConnectionTestTarget();

  if (connectionTestStatus) {
    connectionTestStatusKey = "connectionTestChecking";
    connectionTestStatus.textContent = t(connectionTestStatusKey);
    connectionTestStatus.className = "vpn-overview-updated";
  }

  connectionTestPreparing = true;
  setConnectionTestRunning(true);

  try {
    const target = await resolveMeasurementTarget(serverKey, { refresh: true });
    if (request !== connectionTestRequest) return;
    connectionTestPreparing = false;
    if (!target) {
      connectionTestStatusKey = "connectionTestUnavailable";
      if (connectionTestStatus) {
        connectionTestStatus.textContent = t(connectionTestStatusKey);
        connectionTestStatus.className = "vpn-overview-updated status-error";
      }
      setConnectionTestRunning(false);
      return;
    }
    connectionTestStatusKey = "measuringConnection";
    if (connectionTestStatus) connectionTestStatus.textContent = t(connectionTestStatusKey);
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

    speedtest.onupdate = data => {
      if (activeConnectionTest === speedtest) updateConnectionTestResults(data);
    };
    speedtest.onend = aborted => {
      if (activeConnectionTest === speedtest) finishConnectionTest(aborted);
    };
    speedtest.start();
    speedtest.worker.onerror = error => {
      if (activeConnectionTest !== speedtest) return;
      console.error("Connection test worker failed:", error);
      finishConnectionTest(true);
    };
    connectionTestWatchdog = setTimeout(() => {
      if (activeConnectionTest !== speedtest) return;
      speedtest.abort();
      resetConnectionTestResults();
      finishConnectionTest(true);
    }, 90000);
  } catch (error) {
    if (request !== connectionTestRequest) return;
    connectionTestPreparing = false;
    console.error("Connection test failed:", error);
    finishConnectionTest(true);
  }
}

connectionTestButton?.addEventListener("click", startConnectionTest);

function resetConnectionTestContext() {
  connectionTestRequest++;
  connectionTestPreparing = false;
  if (activeConnectionTest) {
    activeConnectionTest.abort();
    finishConnectionTest(true);
  }
  setConnectionTestRunning(false);
  activeConnectionTestServer = null;
  resetConnectionTestResults();
  renderConnectionTestTarget();
}

window.addEventListener("vpntransportchange", resetConnectionTestContext);
window.addEventListener("tolf:network-context-changed", resetConnectionTestContext);
window.addEventListener("online", resetConnectionTestContext);

for (const input of serverInputs) {
  input.addEventListener("change", resetConnectionTestContext);
}

if (connectionTestStatus) {
  connectionTestStatus.setAttribute("aria-live", "polite");
}

resetConnectionTestResults();
renderConnectionTestTarget();
