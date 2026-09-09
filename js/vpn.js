function setVpnBusy(value) {
  vpnBusy = value;
  for (const button of [createVpnButton, generateProfileButton, rotatePasswordButton,
    deleteVpnButton, deleteAccountButton, signOutButton, redeemPromoButton]) {
    button.disabled = value;
  }
  updateServerAvailability();
  if (localIdInput) localIdInput.disabled = value;
  if (typeof setProfileSettingsBusy === "function") {
    setProfileSettingsBusy(value);
  }
}

createVpnButton.addEventListener("click", async () => {
  try {
    if (vpnBusy) return;

    const selection = getProfileSelection();

    if (!selection) {
      throw new Error("Profile selection is invalid");
    }

    const { server } = selection;

    setVpnBusy(true);
    vpnMessage.textContent = t("creatingVpn");
    vpnMessage.className = "message";

    const data = await apiRequest("/vpn/create", {
      method: "POST",
      body: JSON.stringify(selection)
    });

    showVpn({ ...data.vpn, server: data.vpn?.server || server });
    setInstallLink(data.profileUrl);

    vpnMessage.textContent = t("vpnAccessCreated");
    vpnMessage.className = "message success";
  } catch (error) {
    vpnMessage.textContent = error?.message || "Request failed";
    vpnMessage.className = "message error";
  } finally {
    setVpnBusy(false);
  }
});

generateProfileButton.addEventListener("click", async () => {
  if (vpnBusy) return;
  const selection = getProfileSelection();
  if (!selection) return;
  setVpnBusy(true);
  setInstallLink(null);
  vpnMessage.textContent = t("generatingInstall");
  vpnMessage.className = "message";
  try {
    const data = await apiRequest("/vpn/profile", {
      method: "POST", body: JSON.stringify(selection)
    });
    if (!data.profileUrl) throw new Error(t("installLinkNotReturned"));
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

shareProfileButton.addEventListener("click", async () => {
  const profileUrl = shareProfileButton.dataset.profileUrl;
  if (!profileUrl) return;

  try {
    if (typeof navigator.share === "function") {
      await navigator.share({
        title: "TOLF VPN",
        url: profileUrl
      });
      return;
    }

    await navigator.clipboard.writeText(profileUrl);
    vpnMessage.textContent = t("profileLinkCopied");
    vpnMessage.className = "message success";
  } catch (error) {
    if (error?.name === "AbortError") return;
    vpnMessage.textContent = t("profileShareFailed");
    vpnMessage.className = "message error";
  }
});

rotatePasswordButton.addEventListener("click", async () => {
  if (vpnBusy) return;
  const selection = getProfileSelection();
  if (!selection) return;
  if (!confirmLocalized("changeVpnConfirmTitle", "changeVpnConfirmBody")) return;
  setVpnBusy(true);
  setInstallLink(null);
  vpnMessage.textContent = t("changingVpnPassword");
  vpnMessage.className = "message";
  try {
    const data = await apiRequest("/vpn/rotate", {
      method: "POST", body: JSON.stringify(selection)
    });
    if (!data.profileUrl) throw new Error(t("newProfileNotReturned"));
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
  if (vpnBusy) return;
  if (!confirmLocalized("deleteVpnConfirmTitle", "deleteVpnConfirmBody")) return;
  setVpnBusy(true);
  setInstallLink(null);
  vpnMessage.textContent = t("deletingVpn");
  vpnMessage.className = "message";
  try {
    const data = await apiRequest("/vpn/delete", {
      method: "POST", body: "{}"
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
