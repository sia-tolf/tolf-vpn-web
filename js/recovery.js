showRecoverButton.addEventListener("click", () => openAccountAuth("recover"));

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

