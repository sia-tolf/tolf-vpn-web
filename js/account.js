async function loadAccount() {
  try {
    const data = await apiRequest("/me", {
      method: "GET"
    });

    applyServerAccess(data);
    showVpn(data.vpn);

    await loadPasskeys();
  } catch {
    showSignedOut();
  }
}

signOutButton.addEventListener("click", async () => {
  signOutButton.disabled = true;

  vpnMessage.textContent = t("signingOut");
  vpnMessage.className = "message";

  try {
    await apiRequest("/logout", {
      method: "POST",
      body: "{}"
    });

    signedOutMessage.textContent = "";
    signedOutMessage.className = "message";

    showSignedOut();
  } catch (error) {
    vpnMessage.textContent = error.message;
    vpnMessage.className = "message error";
  } finally {
    signOutButton.disabled = false;
  }
});

signInButton.addEventListener("click", async () => {
  signInButton.disabled = true;

  signedOutMessage.textContent = t("waitingPasskey");
  signedOutMessage.className = "message";

  try {
    const begin = await apiRequest("/passkey/login/begin", {
      method: "POST",
      body: "{}"
    });

    const credential = await navigator.credentials.get({
      publicKey: prepareAuthenticationOptions(begin.options)
    });

    if (!credential) {
      throw new Error(t("passkeyNotProvided"));
    }

    await apiRequest("/passkey/login/finish", {
      method: "POST",
      body: JSON.stringify({
        challengeId: begin.challengeId,
        credential: serializeCredential(credential)
      })
    });

    signedOutMessage.textContent = "";

    await loadAccount();
  } catch (error) {
    signedOutMessage.textContent = error.message;
    signedOutMessage.className = "message error";
  } finally {
    signInButton.disabled = false;
  }
});

createAccountButton.addEventListener("click", async () => {
  createAccountButton.disabled = true;
  signInButton.disabled = true;
  showRecoverButton.disabled = true;

  signedOutMessage.textContent = t("creatingPasskey");
  signedOutMessage.className = "message";

  try {
    const begin = await apiRequest("/passkey/register/begin", {
      method: "POST",
      body: "{}"
    });

    const credential = await navigator.credentials.create({
      publicKey: prepareRegistrationOptions(begin.options)
    });

    if (!credential) {
      throw new Error(t("passkeyNotCreated"));
    }

    const finish = await apiRequest("/passkey/register/finish", {
      method: "POST",
      body: JSON.stringify({
        challengeId: begin.challengeId,
        credential: serializeCredential(credential)
      })
    });

    if (!finish.recoveryCode) {
      throw new Error(t("recoveryCodeNotReturned"));
    }

    showSignedOutRecoveryCode(finish.recoveryCode);

    signedOutMessage.textContent = t("accountCreatedSaveRecovery");
    signedOutMessage.className = "message success";
  } catch (error) {
    signedOutMessage.textContent = error.message;
    signedOutMessage.className = "message error";
  } finally {
    createAccountButton.disabled = false;
    signInButton.disabled = false;
    showRecoverButton.disabled = false;
  }
});

deleteAccountButton.addEventListener("click", async () => {
  const confirmed = confirmLocalized(
    "deleteAccountConfirmTitle",
    "deleteAccountConfirmBody"
  );

  if (!confirmed) {
    return;
  }

  deleteAccountButton.disabled = true;
  signOutButton.disabled = true;
  addPasskeyButton.disabled = true;
  generateRecoveryButton.disabled = true;
  createVpnButton.disabled = true;
  generateProfileButton.disabled = true;
  rotatePasswordButton.disabled = true;
  deleteVpnButton.disabled = true;

  setInstallLink(null);

  vpnMessage.textContent = t("deletingAccount");
  vpnMessage.className = "message";

  try {
    await apiRequest("/account/delete", {
      method: "POST",
      body: JSON.stringify({
        confirm: "DELETE"
      })
    });

    signedOutMessage.textContent = t("accountDeleted");
    signedOutMessage.className = "message success";

    showSignedOut();
  } catch (error) {
    vpnMessage.textContent = error.message;
    vpnMessage.className = "message error";
  } finally {
    deleteAccountButton.disabled = false;
    signOutButton.disabled = false;
    addPasskeyButton.disabled = false;
    generateRecoveryButton.disabled = false;
    createVpnButton.disabled = false;
    generateProfileButton.disabled = false;
    rotatePasswordButton.disabled = false;
    deleteVpnButton.disabled = false;
  }
});
