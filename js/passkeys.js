function formatPasskeyDate(value) {
  if (!value) return "";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat(
    currentLanguage === "ru" ? "ru-RU" : "en-GB",
    {
      day: "numeric",
      month: "short",
      year: "numeric"
    }
  ).format(date);
}

function renderPasskeys(passkeys) {
  lastPasskeys = passkeys;
  passkeyList.textContent = "";

  const total = passkeys.length;

  passkeys.forEach((passkey, index) => {
    const item = document.createElement("div");
    item.className = "passkey-item";

    const info = document.createElement("div");
    info.className = "passkey-info";

    const name = document.createElement("div");
    name.className = "passkey-name";
    name.textContent = passkey.name || (
      total === 1
        ? t("passkeyFallback")
        : `${t("passkeyFallback")} ${index + 1}`
    );

    const meta = document.createElement("div");
    meta.className = "passkey-meta";

    const created = formatPasskeyDate(passkey.createdAt);

    meta.textContent = created
      ? t("addedDate", { date: created })
      : t("registeredPasskey");

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "passkey-remove-button";
    removeButton.textContent = t("remove");

    if (total <= 1) {
      removeButton.disabled = true;
      removeButton.title = t("addAnotherBeforeRemoving");
    } else {
      removeButton.addEventListener("click", async () => {
        const confirmed = confirmLocalized(
          "removePasskeyConfirmTitle",
          "removePasskeyConfirmBody",
          { name: name.textContent }
        );

        if (!confirmed) return;

        removeButton.disabled = true;
        addPasskeyButton.disabled = true;

        passkeyMessage.textContent = t("removingPasskey");
        passkeyMessage.className = "passkey-message";

        try {
          await apiRequest("/passkeys/delete", {
            method: "POST",
            body: JSON.stringify({ id: passkey.id })
          });

          await loadPasskeys();

          passkeyMessage.textContent = t("passkeyRemoved");
          passkeyMessage.className = "passkey-message success";
        } catch (error) {
          passkeyMessage.textContent = error.message;
          passkeyMessage.className = "passkey-message error";
        } finally {
          addPasskeyButton.disabled = false;
        }
      });
    }

    info.appendChild(name);
    info.appendChild(meta);
    item.appendChild(info);
    const actions = document.createElement("div");
    actions.className = "passkey-label-actions";
    actions.appendChild(removeButton);
    item.appendChild(actions);
    passkeyList.appendChild(item);
  });
}

async function loadPasskeys() {
  try {
    const data = await apiRequest("/passkeys", {
      method: "GET"
    });

    renderPasskeys(
      Array.isArray(data.passkeys) ? data.passkeys : []
    );
  } catch (error) {
    passkeyList.textContent = "";
    passkeyMessage.textContent = error.message;
    passkeyMessage.className = "passkey-message error";
  }
}

addPasskeyButton.addEventListener("click", async () => {
  addPasskeyButton.disabled = true;
  deleteAccountButton.disabled = true;

  passkeyMessage.textContent = t("creatingPasskey");
  passkeyMessage.className = "passkey-message";

  try {
    const passkeyName = await checkedPasskeyName("addPasskeyName");
    const begin = await apiRequest("/passkeys/add/begin", {
      method: "POST",
      body: JSON.stringify({ passkeyName })
    });

    const credential = await navigator.credentials.create({
      publicKey: prepareRegistrationOptions(begin.options)
    });

    if (!credential) {
      throw new Error(t("passkeyNotCreated"));
    }

    const finish = await apiRequest("/passkeys/add/finish", {
      method: "POST",
      body: JSON.stringify({
        challengeId: begin.challengeId,
        credential: serializeCredential(credential)
      })
    });

    document.getElementById("addPasskeyName").value = "";
    await loadPasskeys();

    passkeyMessage.textContent = finish.passkeyName
      ? t("passkeyAddedNamed", { name: finish.passkeyName })
      : t("passkeyAdded");

    passkeyMessage.className = "passkey-message success";
  } catch (error) {
    passkeyMessage.textContent = error.message;
    passkeyMessage.className = "passkey-message error";
  } finally {
    addPasskeyButton.disabled = false;
    deleteAccountButton.disabled = false;
  }
});

async function requirePasskeyNaming() {
  try {
    const data = await apiRequest("/passkeys/naming", {method: "GET"});
    if (data.version !== 1) throw new Error();
  } catch {
    throw new Error(t("passkeyNamingUnavailable"));
  }
}
async function checkedPasskeyName(id) {
  const input = document.getElementById(id);
  const value = input.value.trim();
  if (!value || value.length > 80 || /[\u0000-\u001f\u007f-\u009f]/.test(value)) {
    input.focus();
    throw new Error(t("passkeyNameRequired"));
  }
  await requirePasskeyNaming();
  return value;
}
