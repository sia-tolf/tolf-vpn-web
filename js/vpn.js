let profileQrUrl = "";

function profileQrText(key) {
  const language = (typeof currentLanguage === "string" ? currentLanguage : document.documentElement.lang) || "en";
  const copy = {
    en: {
      button: "QR code",
      caption: "Scan this code on another iPhone or iPad to open the profile installation page.",
      error: "Could not create the QR code for this profile."
    },
    ru: {
      button: "QR-код",
      caption: "Отсканируйте этот код на другом iPhone или iPad, чтобы открыть страницу установки профиля.",
      error: "Не удалось создать QR-код для этого профиля."
    },
    lv: {
      button: "QR kods",
      caption: "Noskenējiet šo kodu citā iPhone vai iPad, lai atvērtu profila instalēšanas lapu.",
      error: "Neizdevās izveidot šī profila QR kodu."
    }
  };
  return (copy[language] || copy.en)[key];
}

function createProfileQrMatrix(text) {
  const version = 6;
  const size = 21 + (version - 1) * 4;
  const dataCodewords = 136;
  const blockCount = 2;
  const dataPerBlock = 68;
  const eccPerBlock = 18;
  const bytes = Array.from(text, character => character.charCodeAt(0));

  if (bytes.some(value => value > 0x7f) || bytes.length > 134) {
    throw new Error("Profile URL cannot be encoded as QR");
  }

  const dataBits = [];
  const pushBits = (target, value, count) => {
    for (let bit = count - 1; bit >= 0; bit -= 1) {
      target.push((value >>> bit) & 1);
    }
  };

  pushBits(dataBits, 0x4, 4);
  pushBits(dataBits, bytes.length, 8);
  for (const value of bytes) pushBits(dataBits, value, 8);

  const capacityBits = dataCodewords * 8;
  for (let index = 0; index < Math.min(4, capacityBits - dataBits.length); index += 1) {
    dataBits.push(0);
  }
  while (dataBits.length % 8) dataBits.push(0);

  const data = [];
  for (let offset = 0; offset < dataBits.length; offset += 8) {
    let value = 0;
    for (let bit = 0; bit < 8; bit += 1) value = (value << 1) | dataBits[offset + bit];
    data.push(value);
  }

  let useEcPad = true;
  while (data.length < dataCodewords) {
    data.push(useEcPad ? 0xec : 0x11);
    useEcPad = !useEcPad;
  }

  const gfExp = new Uint8Array(512);
  const gfLog = new Uint8Array(256);
  let fieldValue = 1;
  for (let index = 0; index < 255; index += 1) {
    gfExp[index] = fieldValue;
    gfLog[fieldValue] = index;
    fieldValue <<= 1;
    if (fieldValue & 0x100) fieldValue ^= 0x11d;
  }
  for (let index = 255; index < 512; index += 1) gfExp[index] = gfExp[index - 255];

  const gfMultiply = (left, right) => (
    left === 0 || right === 0 ? 0 : gfExp[gfLog[left] + gfLog[right]]
  );

  let generator = [1];
  for (let degree = 0; degree < eccPerBlock; degree += 1) {
    const next = new Array(generator.length + 1).fill(0);
    for (let index = 0; index < generator.length; index += 1) {
      next[index] ^= generator[index];
      next[index + 1] ^= gfMultiply(generator[index], gfExp[degree]);
    }
    generator = next;
  }

  const makeEcc = block => {
    const remainder = new Array(eccPerBlock).fill(0);
    for (const value of block) {
      const factor = value ^ remainder[0];
      remainder.shift();
      remainder.push(0);
      for (let index = 0; index < eccPerBlock; index += 1) {
        remainder[index] ^= gfMultiply(generator[index + 1], factor);
      }
    }
    return remainder;
  };

  const dataBlocks = [];
  const eccBlocks = [];
  for (let blockIndex = 0; blockIndex < blockCount; blockIndex += 1) {
    const block = data.slice(
      blockIndex * dataPerBlock,
      (blockIndex + 1) * dataPerBlock
    );
    dataBlocks.push(block);
    eccBlocks.push(makeEcc(block));
  }

  const codewords = [];
  for (let index = 0; index < dataPerBlock; index += 1) {
    for (let blockIndex = 0; blockIndex < blockCount; blockIndex += 1) {
      codewords.push(dataBlocks[blockIndex][index]);
    }
  }
  for (let index = 0; index < eccPerBlock; index += 1) {
    for (let blockIndex = 0; blockIndex < blockCount; blockIndex += 1) {
      codewords.push(eccBlocks[blockIndex][index]);
    }
  }

  const stream = [];
  for (const value of codewords) pushBits(stream, value, 8);
  for (let index = 0; index < 7; index += 1) stream.push(0);

  const modules = Array.from({length: size}, () => Array(size).fill(false));
  const functionModules = Array.from({length: size}, () => Array(size).fill(false));
  const setFunctionModule = (row, column, dark) => {
    if (row < 0 || column < 0 || row >= size || column >= size) return;
    modules[row][column] = Boolean(dark);
    functionModules[row][column] = true;
  };

  const drawFinder = (top, left) => {
    for (let rowOffset = -1; rowOffset <= 7; rowOffset += 1) {
      for (let columnOffset = -1; columnOffset <= 7; columnOffset += 1) {
        const inside = columnOffset >= 0 && columnOffset <= 6 && rowOffset >= 0 && rowOffset <= 6;
        const dark = inside && (
          columnOffset === 0 || columnOffset === 6 ||
          rowOffset === 0 || rowOffset === 6 ||
          (columnOffset >= 2 && columnOffset <= 4 && rowOffset >= 2 && rowOffset <= 4)
        );
        setFunctionModule(top + rowOffset, left + columnOffset, dark);
      }
    }
  };

  drawFinder(0, 0);
  drawFinder(0, size - 7);
  drawFinder(size - 7, 0);

  for (let index = 8; index < size - 8; index += 1) {
    setFunctionModule(6, index, index % 2 === 0);
    setFunctionModule(index, 6, index % 2 === 0);
  }

  for (let rowOffset = -2; rowOffset <= 2; rowOffset += 1) {
    for (let columnOffset = -2; columnOffset <= 2; columnOffset += 1) {
      setFunctionModule(
        34 + rowOffset,
        34 + columnOffset,
        Math.max(Math.abs(columnOffset), Math.abs(rowOffset)) !== 1
      );
    }
  }

  const drawFormatBits = mask => {
    const formatData = (1 << 3) | mask;
    let remainder = formatData;
    for (let index = 0; index < 10; index += 1) {
      remainder = (remainder << 1) ^ (((remainder >>> 9) & 1) ? 0x537 : 0);
    }
    const format = ((formatData << 10) | remainder) ^ 0x5412;
    const formatBit = index => ((format >>> index) & 1) !== 0;

    for (let index = 0; index <= 5; index += 1) setFunctionModule(index, 8, formatBit(index));
    setFunctionModule(7, 8, formatBit(6));
    setFunctionModule(8, 8, formatBit(7));
    setFunctionModule(8, 7, formatBit(8));
    for (let index = 9; index < 15; index += 1) setFunctionModule(8, 14 - index, formatBit(index));
    for (let index = 0; index < 8; index += 1) setFunctionModule(8, size - 1 - index, formatBit(index));
    for (let index = 8; index < 15; index += 1) setFunctionModule(size - 15 + index, 8, formatBit(index));
    setFunctionModule(size - 8, 8, true);
  };

  drawFormatBits(0);

  let streamIndex = 0;
  let upward = true;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right -= 1;
    for (let index = 0; index < size; index += 1) {
      const row = upward ? size - 1 - index : index;
      for (let pairOffset = 0; pairOffset < 2; pairOffset += 1) {
        const column = right - pairOffset;
        if (functionModules[row][column]) continue;
        modules[row][column] = streamIndex < stream.length
          ? stream[streamIndex] !== 0
          : false;
        streamIndex += 1;
      }
    }
    upward = !upward;
  }

  for (let row = 0; row < size; row += 1) {
    for (let column = 0; column < size; column += 1) {
      if (!functionModules[row][column] && ((row + column) & 1) === 0) {
        modules[row][column] = !modules[row][column];
      }
    }
  }

  drawFormatBits(0);
  return modules;
}

function drawProfileQr(canvas, text) {
  const matrix = createProfileQrMatrix(text);
  const quietZone = 4;
  const pixelsPerModule = 8;
  const totalModules = matrix.length + quietZone * 2;
  canvas.width = totalModules * pixelsPerModule;
  canvas.height = totalModules * pixelsPerModule;

  const context = canvas.getContext("2d", {alpha: false});
  context.imageSmoothingEnabled = false;
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#000000";

  for (let row = 0; row < matrix.length; row += 1) {
    for (let column = 0; column < matrix.length; column += 1) {
      if (!matrix[row][column]) continue;
      context.fillRect(
        (column + quietZone) * pixelsPerModule,
        (row + quietZone) * pixelsPerModule,
        pixelsPerModule,
        pixelsPerModule
      );
    }
  }
}

const profileQrStyle = document.createElement("style");
profileQrStyle.textContent = `
  .profile-delivery-actions {
    flex: 0 0 100%;
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }
  .profile-delivery-actions.hidden { display: none !important; }
  .profile-delivery-actions > .button-link { width: 100%; min-width: 0; }
  .profile-qr-panel {
    grid-column: 1 / -1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 18px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--code-background);
  }
  .profile-qr-panel.hidden { display: none !important; }
  .profile-qr-canvas {
    display: block;
    width: min(260px, 100%);
    height: auto;
    border-radius: 10px;
    background: #ffffff;
    image-rendering: pixelated;
  }
  .profile-qr-caption {
    max-width: 380px;
    margin: 0;
    color: var(--secondary);
    font-size: 14px;
    line-height: 1.45;
    text-align: center;
  }
  @media (max-width: 620px) {
    .profile-delivery-actions { grid-template-columns: minmax(0, 1fr); }
    .profile-qr-panel { grid-column: 1; }
  }
`;
document.head.appendChild(profileQrStyle);

const profileQrButton = document.createElement("button");
profileQrButton.id = "profileQrButton";
profileQrButton.className = "button-link secondary";
profileQrButton.type = "button";
profileQrButton.setAttribute("aria-expanded", "false");
profileQrButton.textContent = profileQrText("button");

const profileQrPanel = document.createElement("div");
profileQrPanel.id = "profileQrPanel";
profileQrPanel.className = "profile-qr-panel hidden";

const profileQrCanvas = document.createElement("canvas");
profileQrCanvas.className = "profile-qr-canvas";
profileQrCanvas.setAttribute("role", "img");
profileQrCanvas.setAttribute("aria-label", "QR code");

const profileQrCaption = document.createElement("p");
profileQrCaption.className = "profile-qr-caption";
profileQrCaption.textContent = profileQrText("caption");

profileQrPanel.append(profileQrCanvas, profileQrCaption);
profileDeliveryActions.append(profileQrButton, profileQrPanel);

const setInstallLinkWithoutQr = setInstallLink;
setInstallLink = function setInstallLinkWithQr(profileUrl) {
  setInstallLinkWithoutQr(profileUrl);
  profileQrUrl = profileUrl ? String(profileUrl) : "";
  profileQrPanel.classList.add("hidden");
  profileQrButton.setAttribute("aria-expanded", "false");
  profileQrCanvas.width = 0;
  profileQrCanvas.height = 0;
};

profileQrButton.addEventListener("click", () => {
  if (!profileQrUrl) return;

  const willOpen = profileQrPanel.classList.contains("hidden");
  if (!willOpen) {
    profileQrPanel.classList.add("hidden");
    profileQrButton.setAttribute("aria-expanded", "false");
    return;
  }

  try {
    drawProfileQr(profileQrCanvas, profileQrUrl);
    profileQrCaption.textContent = profileQrText("caption");
    profileQrPanel.classList.remove("hidden");
    profileQrButton.setAttribute("aria-expanded", "true");
  } catch {
    vpnMessage.textContent = profileQrText("error");
    vpnMessage.className = "message error";
  }
});

new MutationObserver(() => {
  profileQrButton.textContent = profileQrText("button");
  profileQrCaption.textContent = profileQrText("caption");
}).observe(document.documentElement, {attributes: true, attributeFilter: ["lang"]});

function setVpnBusy(value) {
  vpnBusy = value;
  for (const id of ["platformIos", "platformAndroid", "platformWindows"]) document.getElementById(id).disabled = value;
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

function confirmVpnDeletion() {
  return new Promise(resolve => {
    const dialog = document.createElement("dialog");
    dialog.setAttribute("aria-labelledby", "vpnDeleteTitle");
    dialog.setAttribute("aria-describedby", "vpnDeleteDescription");
    dialog.style.cssText = "box-sizing:border-box;width:calc(100% - 32px);max-width:420px;padding:24px;border:1px solid var(--border);border-radius:16px;background:var(--card);color:var(--text)";
    const title = document.createElement("h2");
    title.id = "vpnDeleteTitle";
    title.textContent = t("deleteVpnConfirmTitle");
    title.style.cssText = "margin:0 0 12px;font-size:20px";
    const description = document.createElement("p");
    description.id = "vpnDeleteDescription";
    description.textContent = t("deleteVpnConfirmBody");
    description.style.cssText = "line-height:1.5;margin:0 0 20px";
    const actions = document.createElement("div");
    actions.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:12px";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "secondary";
    cancel.textContent = t("cancelButton");
    cancel.autofocus = true;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "danger";
    remove.textContent = {en:"Delete",ru:"Удалить",lv:"Dzēst"}[currentLanguage] || "Delete";
    cancel.addEventListener("click", () => dialog.close("cancel"));
    remove.addEventListener("click", () => dialog.close("delete"));
    dialog.addEventListener("close", () => {
      const confirmed = dialog.returnValue === "delete";
      dialog.remove();
      resolve(confirmed);
    }, {once:true});
    actions.append(cancel, remove);
    dialog.append(title, description, actions);
    document.body.appendChild(dialog);
    dialog.showModal();
  });
}

deleteVpnButton.addEventListener("click", async () => {
  if (vpnBusy) return;
  if (!await confirmVpnDeletion()) return;
  if (vpnBusy) return;
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
