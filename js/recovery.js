showRecoverButton.addEventListener("click", () => {
  signedOutMainActions.classList.add("hidden");
  recoverPanel.classList.remove("hidden");

  signedOutMessage.textContent = "";
  signedOutMessage.className = "message";

  recoveryInput.focus();
});

cancelRecoverButton.addEventListener("click", () => {
  recoveryInput.value = "";

  recoverPanel.classList.add("hidden");
  signedOutMainActions.classList.remove("hidden");

  signedOutMessage.textContent = "";
});

copySignedOutRecoveryButton.addEventListener("click", async () => {
  const code = signedOutRecoveryCode.textContent;

  if (!code) return;

  try {
    await copyText(code);

    signedOutMessage.textContent = t("recoveryCodeCopied");
    signedOutMessage.className = "message success";
  } catch {
    signedOutMessage.textContent = t("recoveryCodeCopyFailed");
    signedOutMessage.className = "message error";
  }
});

savedSignedOutRecoveryButton.addEventListener("click", () => {
  hideSignedOutRecoveryCode();

  signedOutMessage.textContent = t("recoveryCodeSavedSignIn");
  signedOutMessage.className = "message success";
});

copyAccountRecoveryButton.addEventListener("click", async () => {
  const code = accountRecoveryCode.textContent;

  if (!code) return;

  try {
    await copyText(code);

    recoveryMessage.textContent = t("recoveryCodeCopied");
    recoveryMessage.className = "recovery-message success";
  } catch {
    recoveryMessage.textContent = t("recoveryCodeCopyFailed");
    recoveryMessage.className = "recovery-message error";
  }
});

savedAccountRecoveryButton.addEventListener("click", () => {
  hideAccountRecoveryCode();

  recoveryMessage.textContent = t("recoveryCodeSaved");
  recoveryMessage.className = "recovery-message success";
});

generateRecoveryButton.addEventListener("click", async () => {
  const confirmed = confirmLocalized(
    "generateRecoveryConfirmTitle",
    "generateRecoveryConfirmBody"
  );

  if (!confirmed) return;

  generateRecoveryButton.disabled = true;
  deleteAccountButton.disabled = true;

  hideAccountRecoveryCode();

  recoveryMessage.textContent = t("generatingRecovery");
  recoveryMessage.className = "recovery-message";

  try {
    const data = await apiRequest("/recovery/regenerate", {
      method: "POST",
      body: "{}"
    });

    if (!data.recoveryCode) {
      throw new Error(t("recoveryCodeNotReturned"));
    }

    showAccountRecoveryCode(data.recoveryCode);

    recoveryMessage.textContent = t("newRecoveryGenerated");
    recoveryMessage.className = "recovery-message success";
  } catch (error) {
    recoveryMessage.textContent = error.message;
    recoveryMessage.className = "recovery-message error";
  } finally {
    generateRecoveryButton.disabled = false;
    deleteAccountButton.disabled = false;
  }
});

recoverAccountButton.addEventListener("click", async () => {
  const recoveryCode = recoveryInput.value.trim().toUpperCase();

  if (!recoveryCode) {
    signedOutMessage.textContent = t("enterRecoveryCode");
    signedOutMessage.className = "message error";
    return;
  }

  recoverAccountButton.disabled = true;
  cancelRecoverButton.disabled = true;

  signedOutMessage.textContent = t("checkingRecovery");
  signedOutMessage.className = "message";

  try {
    const begin = await apiRequest("/recovery/begin", {
      method: "POST",
      body: JSON.stringify({ recoveryCode })
    });

    signedOutMessage.textContent = t("creatingNamedPasskey", {
      name: begin.passkeyName || t("newPasskey")
    });

    const credential = await navigator.credentials.create({
      publicKey: prepareRegistrationOptions(begin.options)
    });

    if (!credential) {
      throw new Error(t("passkeyNotCreated"));
    }

    const finish = await apiRequest("/recovery/finish", {
      method: "POST",
      body: JSON.stringify({
        challengeId: begin.challengeId,
        credential: serializeCredential(credential)
      })
    });

    if (!finish.recoveryCode) {
      throw new Error(t("newRecoveryCodeNotReturned"));
    }

    recoveryInput.value = "";

    showSignedOutRecoveryCode(finish.recoveryCode);

    signedOutMessage.textContent = t("recoveredPasskeyCreated", {
      name: finish.passkeyName || t("newPasskey")
    });

    signedOutMessage.className = "message success";
  } catch (error) {
    signedOutMessage.textContent = error.message;
    signedOutMessage.className = "message error";
  } finally {
    recoverAccountButton.disabled = false;
    cancelRecoverButton.disabled = false;
  }
});
