const registerPanel = document.getElementById("registerPanel");
const submitRegisterButton = document.getElementById("submitRegisterButton");
const cancelRegisterButton = document.getElementById("cancelRegisterButton");

function closeRegistrationPanel() {
  registerPanel.classList.add("hidden");
}

function openRegistrationPanel() {
  signedOutMainActions.classList.add("hidden");
  recoverPanel.classList.add("hidden");
  registerPanel.classList.remove("hidden");
  signedOutMessage.textContent = "";
  signedOutMessage.className = "message";
  document.getElementById("registerPasskeyName").focus();
}

function handleEntryAction() {
  const url = new URL(window.location.href);
  const action = url.searchParams.get("action");
  const requestedLanguage = url.searchParams.get("lang");

  if (["en", "ru", "lv"].includes(requestedLanguage)) {
    setLanguage(requestedLanguage);
  }

  if (action === "signup") {
    openRegistrationPanel();
  } else if (action === "signin") {
    closeRegistrationPanel();
    recoverPanel.classList.add("hidden");
    signedOutMainActions.classList.remove("hidden");
    signedOutMessage.textContent = "";
    signedOutMessage.className = "message";

    requestAnimationFrame(() => {
      signInButton.focus({ preventScroll: true });
      signedOutCard.scrollIntoView({ block: "start" });
    });
  } else if (!["en", "ru", "lv"].includes(requestedLanguage)) {
    return;
  }

  url.searchParams.delete("action");
  url.searchParams.delete("lang");
  window.history.replaceState({}, "", url.pathname + url.search + url.hash);
}

createAccountButton.addEventListener("click", openRegistrationPanel);

cancelRegisterButton.addEventListener("click", () => {
  closeRegistrationPanel();
  signedOutMainActions.classList.remove("hidden");
  signedOutMessage.textContent = "";
  createAccountButton.focus();
});

async function loadAccount() {
  try {
    const data = await apiRequest("/me", {
      method: "GET"
    });

    applyServerAccess(data);
    showVpn(data.vpn);

    await loadPasskeys();
    await updateInvitationAccount(data);
  } catch {
    showSignedOut();
    handleEntryAction();
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

    const language = ["en", "ru", "lv"].includes(currentLanguage)
      ? currentLanguage
      : "en";

    window.location.assign(
      `https://tolf.is/?lang=${encodeURIComponent(language)}`
    );
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

submitRegisterButton.addEventListener("click", async () => {
  if (submitRegisterButton.disabled) return;
  submitRegisterButton.disabled = true;
  cancelRegisterButton.disabled = true;
  createAccountButton.disabled = true;
  signInButton.disabled = true;
  showRecoverButton.disabled = true;

  signedOutMessage.textContent = t("creatingPasskey");
  signedOutMessage.className = "message";

  try {
    const passkeyName = await checkedPasskeyName("registerPasskeyName");
    const begin = await apiRequest("/passkey/register/begin", {
      method: "POST",
      body: JSON.stringify({ passkeyName })
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
    submitRegisterButton.disabled = false;
    cancelRegisterButton.disabled = false;
    createAccountButton.disabled = false;
    signInButton.disabled = false;
    showRecoverButton.disabled = false;
  }
});

deleteAccountButton.addEventListener("click", async () => {
  if (typeof invitationProtected !== "undefined" && invitationProtected) {
    window.alert(t("protectedAccountDelete"));
    return;
  }

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
