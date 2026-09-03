createVpnButton.addEventListener("click", async () => {
  createVpnButton.disabled = true;

  vpnMessage.textContent = t("creatingVpn");
  vpnMessage.className = "message";

  try {
    const server = getSelectedServerKey();

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
    createVpnButton.disabled = false;
  }
});

generateProfileButton.addEventListener("click", async () => {
  generateProfileButton.disabled = true;

  setInstallLink(null);

  vpnMessage.textContent = t("generatingInstall");
  vpnMessage.className = "message";

  try {
    const data = await apiRequest("/vpn/profile", {
      method: "POST",
      body: "{}"
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
    generateProfileButton.disabled = false;
  }
});

rotatePasswordButton.addEventListener("click", async () => {
  const confirmed = confirmLocalized(
    "changeVpnConfirmTitle",
    "changeVpnConfirmBody"
  );

  if (!confirmed) return;

  rotatePasswordButton.disabled = true;
  generateProfileButton.disabled = true;
  deleteVpnButton.disabled = true;
  deleteAccountButton.disabled = true;

  setInstallLink(null);

  vpnMessage.textContent = t("changingVpnPassword");
  vpnMessage.className = "message";

  try {
    const data = await apiRequest("/vpn/rotate", {
      method: "POST",
      body: "{}"
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
    rotatePasswordButton.disabled = false;
    generateProfileButton.disabled = false;
    deleteVpnButton.disabled = false;
    deleteAccountButton.disabled = false;
  }
});

deleteVpnButton.addEventListener("click", async () => {
  const confirmed = confirmLocalized(
    "deleteVpnConfirmTitle",
    "deleteVpnConfirmBody"
  );

  if (!confirmed) return;

  deleteVpnButton.disabled = true;
  rotatePasswordButton.disabled = true;
  generateProfileButton.disabled = true;
  deleteAccountButton.disabled = true;

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
    deleteVpnButton.disabled = false;
    rotatePasswordButton.disabled = false;
    generateProfileButton.disabled = false;
    deleteAccountButton.disabled = false;
  }
});
