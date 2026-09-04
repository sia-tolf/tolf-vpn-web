function getSelectedServerKey() {
  const selected = document.querySelector('input[name="vpnServer"]:checked');
  return allowedServers.includes(selected?.value) ? selected.value : "riga";
}

function updateSelectedServerAddress() {
  const server = SERVERS[getSelectedServerKey()];
  selectedServerAddress.textContent = server?.host || "";
  renderLocalIdSettings();
}

function getSelectedLocalId() {
  const server = getSelectedServerKey();
  return (localIdValues[server] || "").trim().toLowerCase() || LOCAL_ID_DEFAULTS[server];
}

function renderLocalIdSettings() {
  if (!localIdInput) return;
  const server = getSelectedServerKey();
  const options = LOCAL_ID_OPTIONS[server];
  const localId = getSelectedLocalId();
  const values = Object.keys(options).map(value => value || t("localIdEmpty")).join(", ");
  const known = Object.hasOwn(options, localId);

  localIdInput.value = localIdValues[server] || "";
  localIdInput.placeholder = t(server === "riga" ? "localIdDefaultRiga" : "localIdDefaultMoscow");
  localIdInput.disabled = vpnBusy;
  localIdChoices.textContent = t("localIdChoices", { values });
  localIdRoutingHint.textContent = known
    ? t(options[localId])
    : t("localIdUnsupported", { values });
  localIdRoutingHint.className = known
    ? "local-id-routing"
    : "local-id-routing error";
  localIdInput.setAttribute("aria-invalid", String(!known));
}

function getProfileSelection() {
  const server = getSelectedServerKey();
  const localId = getSelectedLocalId();
  if (!Object.hasOwn(LOCAL_ID_OPTIONS[server], localId)) {
    renderLocalIdSettings();
    profileSettings.open = true;
    localIdInput.focus();
    return null;
  }
  return { server, localId };
}

localIdInput?.addEventListener("input", () => {
  localIdValues[getSelectedServerKey()] = localIdInput.value;
  setInstallLink(null);
  vpnMessage.textContent = "";
  vpnMessage.className = "message";
  renderLocalIdSettings();
});

function showConfiguredServer(vpn) {
  const serverKey = getSelectedServerKey();
  const server = SERVERS[serverKey];
  vpnServerName.textContent = t(server.nameKey);
  vpnServerHost.textContent = server.host;
  serverRow.classList.remove("hidden");
}

for (const input of serverInputs) {
  input.addEventListener("change", () => {
    setInstallLink(null);
    vpnMessage.textContent = "";
    vpnMessage.className = "message";
    updateSelectedServerAddress();
    if (lastVpnState) renderVpnState(lastVpnState);
  });
}

function showSignedOutRecoveryCode(recoveryCode) {
  signedOutRecoveryCode.textContent = recoveryCode;
  signedOutRecoveryBox.classList.remove("hidden");
  signedOutMainActions.classList.add("hidden");
  recoverPanel.classList.add("hidden");
}

function hideSignedOutRecoveryCode() {
  signedOutRecoveryCode.textContent = "";
  signedOutRecoveryBox.classList.add("hidden");
  signedOutMainActions.classList.remove("hidden");
}

function showAccountRecoveryCode(recoveryCode) {
  accountRecoveryCode.textContent = recoveryCode;
  accountRecoveryBox.classList.remove("hidden");
}

function hideAccountRecoveryCode() {
  accountRecoveryCode.textContent = "";
  accountRecoveryBox.classList.add("hidden");
}

function setInstallLink(profileUrl) {
  if (profileUrl) {
    installProfileButton.href = profileUrl;
    installProfileButton.classList.remove("hidden");
    generateProfileButton.classList.remove("primary");
    generateProfileButton.classList.add("secondary");
  } else {
    installProfileButton.href = "#";
    installProfileButton.classList.add("hidden");
    generateProfileButton.classList.remove("secondary");
    generateProfileButton.classList.add("primary");
  }
}

function showSignedOut() {
  loadingCard.classList.add("hidden");
  vpnCard.classList.add("hidden");
  signedOutCard.classList.remove("hidden");
  setInstallLink(null);
  passkeyList.textContent = "";
  lastPasskeys = [];
  passkeyMessage.textContent = "";
  passkeyMessage.className = "passkey-message";
  recoveryMessage.textContent = "";
  recoveryMessage.className = "recovery-message";
  hideAccountRecoveryCode();
  lastVpnState = null;
  promoInput.value = "";
  promoMessage.textContent = "";
  promoMessage.className = "promo-message";
  applyServerAccess({
    allowedServers: ["riga", "moscow"],
    promoRedeemed: false,
    promoPending: false
  });
  localIdValues = { riga: "", moscow: "" };
  if (profileSettings) profileSettings.open = false;
  renderLocalIdSettings();
}

function renderVpnState(vpn) {
  lastVpnState = vpn;
  updateSelectedServerAddress();

  if (vpn.configured) {
    vpnStatus.textContent = t("active");
    vpnStatus.className = "row-value status-active";
    serverSection.classList.remove("hidden");
    showConfiguredServer(vpn);
    vpnUsername.textContent = vpn.username || "";
    usernameRow.classList.remove("hidden");
    createVpnButton.classList.add("hidden");
    generateProfileButton.classList.remove("hidden");
    rotatePasswordButton.classList.remove("hidden");
    rotatePasswordNote.classList.remove("hidden");
    deleteSection.classList.remove("hidden");
  } else {
    vpnStatus.textContent = t("notConfigured");
    vpnStatus.className = "row-value";
    serverRow.classList.add("hidden");
    vpnServerName.textContent = "";
    vpnServerHost.textContent = "";
    serverSection.classList.remove("hidden");
    vpnUsername.textContent = "";
    usernameRow.classList.add("hidden");
    generateProfileButton.classList.add("hidden");
    rotatePasswordButton.classList.add("hidden");
    rotatePasswordNote.classList.add("hidden");
    deleteSection.classList.add("hidden");
    createVpnButton.classList.remove("hidden");
  }
}

function showVpn(vpn) {
  loadingCard.classList.add("hidden");
  signedOutCard.classList.add("hidden");
  vpnCard.classList.remove("hidden");
  setInstallLink(null);
  vpnMessage.textContent = "";
  vpnMessage.className = "message";
  renderVpnState(vpn);
}
