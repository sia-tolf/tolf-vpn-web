showRecoverButton.addEventListener("click", () => openAccountAuth("recover"));

cancelRecoverButton.addEventListener("click", () => {
  recoveryInput.value = "";

  recoverPanel.classList.add("hidden");
  signedOutMainActions.classList.remove("hidden");

  signedOutMessage.textContent = "";
});

saveSignedOutRecoveryButton.addEventListener("click", async () => {
  const code = signedOutRecoveryCode.textContent.trim();
  if (!code) return;

  const details = signedOutRecoveryDetails || {};
  const lines = [t("recoveryFileTitle"), ""];
  if (details.userId) {
    lines.push(`${t("recoveryFileAccountId")}: ${details.userId}`);
  }
  if (details.passkeyName) {
    lines.push(`${t("recoveryFilePasskey")}: ${details.passkeyName}`);
  }
  lines.push(`${t("recoveryFileCode")}: ${code}`, "");

  try {
    const file = new File(
      [String.fromCharCode(0xFEFF), lines.join(String.fromCharCode(10))],
      "TOLF-Recovery-Code.txt",
      { type: "text/plain;charset=utf-8" }
    );

    if (typeof navigator.share === "function" &&
        navigator.canShare?.({ files: [file] })) {
      try {
        await navigator.share({ files: [file] });
        return;
      } catch (error) {
        if (error?.name === "AbortError") return;
      }
    }

    const url = URL.createObjectURL(file);
    const link = document.createElement("a");
    link.href = url;
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    signedOutMessage.textContent = t("recoveryFileFailed");
    signedOutMessage.className = "message error";
  }
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

    showSignedOutRecoveryCode(finish.recoveryCode, finish);

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

