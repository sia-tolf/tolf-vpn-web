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

