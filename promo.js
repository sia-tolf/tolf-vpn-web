function updateServerAvailability() {
  for (const input of serverInputs) {
    input.disabled = vpnBusy || !allowedServers.includes(input.value);

    if (input.checked && !allowedServers.includes(input.value)) {
      input.checked = false;
      document.getElementById("serverRiga").checked = true;
    }
  }
}

function renderPromoState() {
  const unlocked = allowedServers.includes("moscow");

  moscowAccessLabel.textContent = unlocked ? "" : t("promoRequired");
  moscowAccessLabel.classList.toggle("hidden", unlocked);

  promoForm.classList.toggle("hidden", unlocked);
  promoGranted.classList.toggle("hidden", !unlocked);

  promoInput.classList.toggle("hidden", promoPending);
  promoInput.setAttribute("aria-label", t("promoCode"));

  redeemPromoButton.textContent = t(
    promoPending ? "retryPromo" : "applyPromo"
  );
}

function applyServerAccess(data) {
  allowedServers =
    Array.isArray(data.allowedServers) &&
    data.allowedServers.includes("moscow")
      ? ["riga", "moscow"]
      : ["riga"];

  promoPending = Boolean(data.promoPending);

  updateServerAvailability();
  renderPromoState();
}

redeemPromoButton.addEventListener("click", async () => {
  if (vpnBusy) {
    return;
  }

  const code = promoInput.value.trim();

  if (!code && !promoPending) {
    promoMessage.textContent = t("enterPromo");
    promoMessage.className = "promo-message error";
    promoInput.focus();
    return;
  }

  setVpnBusy(true);

  promoMessage.textContent = t("checkingPromo");
  promoMessage.className = "promo-message";

  try {
    const data = await apiRequest("/promo/redeem", {
      method: "POST",
      body: JSON.stringify({ code })
    });

    applyServerAccess(data);

    promoInput.value = "";

    document.getElementById("serverMoscow").checked = true;
    document.getElementById("serverRiga").checked = false;

    setInstallLink(null);
    updateSelectedServerAddress();

    if (lastVpnState) {
      renderVpnState(lastVpnState);
    }

    promoMessage.textContent = t("promoAccepted");
    promoMessage.className = "promo-message success";
  } catch (error) {
    const messages = {
      "Promo code is invalid or no longer available.": "invalidPromo",
      "Too many promo attempts. Try again in 15 minutes.": "promoRateLimit"
    };

    promoMessage.textContent = messages[error.message]
      ? t(messages[error.message])
      : error.message;

    promoMessage.className = "promo-message error";
  } finally {
    setVpnBusy(false);
  }
});

promoInput.addEventListener("keydown", event => {
  if (event.key === "Enter") {
    event.preventDefault();
    redeemPromoButton.click();
  }
});
