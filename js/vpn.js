function setVpnBusy(value) {
  vpnBusy = value;

  for (const button of [
    createVpnButton,
    generateProfileButton,
    rotatePasswordButton,
    deleteVpnButton,
    deleteAccountButton,
    signOutButton,
    redeemPromoButton
  ]) {
    button.disabled = value;
  }

  updateServerAvailability();
}

createVpnButton.addEventListener("click", async () => {
  if (vpnBusy) {
    return;
  }

  const server = getSelectedServerKey();

  setVpnBusy(true);

  vpnMessage.textContent = t("creatingVpn");
  vpnMessage.className = "message";

  try {
    const data = await apiRequest("/vpn/create", {
      method: "POST",
      body: JSON.stringify({ server })
    });

    showVpn({
      ...data.vpn,
      server: data.vpn?.server || server
    });

    setInstallLink(data.profileUrl);

    vpnMessage.textContent = t("vpnAccessCreated");
    vpnMessage.className = "message success";
  } catch (error) {
    vpnMessage.textContent = error.message;
    vpnMessage.className = "message error";
  } finally {
    setVpnBusy(false);
  }
});

generateProfileButton.addEventListener("click", async () => {
  if (vpnBusy) {
    return;
  }

  const server = getSelectedServerKey();

  setVpnBusy(true);
  setInstallLink(null);

  vpnMessage.textContent = t("generatingInstall");
  vpnMessage.className = "message";

  try {
    const data = await apiRequest("/vpn/profile", {
      method: "POST",
      body: JSON.stringify({ server })
    });

    if (!data.profileUrl) {
      throw new Error(t("installLinkNotReturned"));
    }

    setInstallLink(data.profileUrl);

    vpnMessage.textContent = t("installLinkReady");
    vpnMessage.className = "message success";
  } catch (error) {
    vpnMessage.textContent = error.message;
    vpnMessage.className = "message error";
  } finally {
    setVpnBusy(false);
  }
});

rotatePasswordButton.addEventListener("click", async () => {
  if (vpnBusy) {
    return;
  }

  if (!confirmLocalized(
    "changeVpnConfirmTitle",
    "changeVpnConfirmBody"
  )) {
    return;
  }

  const server = getSelectedServerKey();

  setVpnBusy(true);
  setInstallLink(null);

  vpnMessage.textContent = t("changingVpnPassword");
  vpnMessage.className = "message";

  try {
    const data = await apiRequest("/vpn/rotate", {
      method: "POST",
      body: JSON.stringify({ server })
    });

    if (!data.profileUrl) {
      throw new Error(t("newProfileNotReturned"));
    }

    setInstallLink(data.profileUrl);

    vpnMessage.textContent = t("vpnPasswordChanged");
    vpnMessage.className = "message success";
  } catch (error) {
    vpnMessage.textContent = error.message;
    vpnMessage.className = "message error";
  } finally {
    setVpnBusy(false);
  }
});

deleteVpnButton.addEventListener("click", async () => {
  if (vpnBusy) {
    return;
  }

  if (!confirmLocalized(
    "deleteVpnConfirmTitle",
    "deleteVpnConfirmBody"
  )) {
    return;
  }

  setVpnBusy(true);
  setInstallLink(null);

  vpnMessage.textContent = t("deletingVpn");
  vpnMessage.className = "message";

  try {
    const data = await apiRequest("/vpn/delete", {
      method: "POST",
      body: "{}"
    });

    showVpn(data.vpn);

    vpnMessage.textContent = t("vpnDeleted");
    vpnMessage.className = "message success";
  } catch (error) {
    vpnMessage.textContent = error.message;
    vpnMessage.className = "message error";
  } finally {
    setVpnBusy(false);
  }
});
