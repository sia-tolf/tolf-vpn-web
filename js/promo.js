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
  moscowAccessLabel.textContent = "";
  moscowAccessLabel.classList.add("hidden");
  promoForm.classList.toggle("hidden", promoRedeemed);
  promoGranted.classList.toggle("hidden", !promoRedeemed);
  promoInput.classList.toggle("hidden", promoPending);
  promoInput.setAttribute("aria-label", t("promoCode"));
  redeemPromoButton.textContent = t(
    promoPending ? "retryPromo" : "applyPromo"
  );
}

function applyServerAccess(data) {
  allowedServers = ["riga", "moscow"];
  promoRedeemed = Boolean(data.promoRedeemed);
  promoPending = Boolean(data.promoPending);
  updateServerAvailability();
  renderPromoState();

  if (typeof selectRecommendedEntryPoint === "function") {
    selectRecommendedEntryPoint();
  }
}

redeemPromoButton.addEventListener("click", async () => {
  if (vpnBusy) return;

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
