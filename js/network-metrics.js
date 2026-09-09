async function loadNetworkMetrics() {
  if (
    !networkMetrics ||
    !networkMetricLatency ||
    !networkMetricRigaToMoscow ||
    !networkMetricMoscowToRiga ||
    !networkMetricMeasuredAt
  ) {
    return;
  }

  try {
    const response = await fetch(
      "https://api.tolf.is/network-metrics",
      {
        cache: "no-store"
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    networkMetricLatency.textContent =
      Number.isFinite(data.rtt_ms)
        ? `${data.rtt_ms.toFixed(1)} ms`
        : "—";

    networkMetricRigaToMoscow.textContent =
      Number.isFinite(data.riga_to_moscow_mbps)
        ? `${Math.round(data.riga_to_moscow_mbps)} Mbps`
        : "—";

    networkMetricMoscowToRiga.textContent =
      Number.isFinite(data.moscow_to_riga_mbps)
        ? `${Math.round(data.moscow_to_riga_mbps)} Mbps`
        : "—";

    if (data.measured_at) {
      const measured = new Date(data.measured_at);

      const locale =
        currentLanguage === "ru"
          ? "ru-RU"
          : currentLanguage === "lv"
            ? "lv-LV"
            : "en-GB";

      networkMetricMeasuredAt.textContent =
        Number.isNaN(measured.getTime())
          ? "—"
          : measured.toLocaleString(locale, {
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit"
            });
    } else {
      networkMetricMeasuredAt.textContent = "—";
    }

    networkMetrics.classList.remove("hidden");
  } catch (error) {
    console.error("Network metrics failed:", error);
    networkMetrics.classList.add("hidden");
  }
}

loadNetworkMetrics();

window.setInterval(loadNetworkMetrics, 300000);
