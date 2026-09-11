let windowsDevices = [];
let windowsEpoch = 0;
let windowsRequestId = null;
let windowsProfileUrl = null;
let windowsReady = false;
const windowsList = document.getElementById('windowsDeviceList');
const windowsMessage = document.getElementById('windowsMessage');
const windowsForm = document.getElementById('windowsCreateForm');
const windowsName = document.getElementById('windowsDeviceName');
const windowsDelivery = document.getElementById('windowsDelivery');

function clearWindowsDevices() {
  windowsEpoch++;
  windowsDevices = [];
  windowsRequestId = null;
  windowsName.value = '';
  windowsMessage.textContent = '';
  setWindowsLink(null);
  renderWindowsDevices();
}

function setWindowsLink(url) {
  windowsProfileUrl = url;
  const link = document.getElementById('windowsInstallLink');
  link.classList.toggle("hidden", !/Windows NT/i.test(navigator.userAgent || ""));
  if (url) link.href = url;
  else link.removeAttribute('href');
  windowsDelivery.classList.toggle('hidden', !url);
}

function renderWindowsDevices() {
  if (windowsName.validity && windowsName.validity.customError) {
    windowsName.setCustomValidity(t('windowsNameRequired'));
  }
  windowsList.replaceChildren();
  for (const device of windowsDevices) {
    const card = document.createElement('section');
    card.className = 'windows-device vpn-overview-card';
    const name = document.createElement('h4'); name.textContent = device.name;
    const user = document.createElement('p');
    user.textContent = device.username || t('windowsPreparing');
    user.className = 'windows-device-username';
    const actions = document.createElement('div'); actions.className = 'actions';
    const download = document.createElement('button'); download.type = 'button';
    download.className = 'constructive';
    download.textContent = t(device.state === 'active' ? 'windowsReissue' : 'windowsContinue');
    download.disabled = vpnBusy || device.state === 'deleting';
    download.addEventListener('click', () => windowsAction(async () => {
      const data = await apiRequest(`/windows/devices/${encodeURIComponent(device.id)}/profile`, {
        method: 'POST', body: JSON.stringify({language: currentLanguage})
      });
      setWindowsLink(data.profileUrl);
      windowsRequestId = null;
      windowsMessage.textContent = t('windowsReady');
    }));
    const remove = document.createElement('button'); remove.type = 'button';
    remove.className = 'danger'; remove.textContent = t('windowsDelete'); remove.disabled = vpnBusy;
    remove.addEventListener('click', () => {
      if (!window.confirm(t('windowsDeleteConfirm', {name: device.name}))) return;
      windowsAction(async () => {
        await apiRequest(`/windows/devices/${encodeURIComponent(device.id)}/delete`, {method:'POST',body:'{}'});
        windowsRequestId = null;
        setWindowsLink(null);
        windowsMessage.textContent = t('windowsDeleted');
      });
    });
    actions.append(download, remove); card.append(name, user, actions); windowsList.append(card);
  }
  document.getElementById('windowsCreateButton').disabled = vpnBusy || !windowsReady;
  windowsName.disabled = vpnBusy;
  document.getElementById("windowsBackButton").disabled = vpnBusy;
}

async function loadWindowsDevices() {
  if (!lastVpnState || !windowsReady) return;
  const epoch = windowsEpoch;
  try {
    const data = await apiRequest('/windows/devices', {method:'GET',cache:'no-store'});
    if (epoch !== windowsEpoch) return;
    windowsDevices = data.devices;
    renderWindowsDevices();
  } catch (error) {
    if (epoch === windowsEpoch) {
      windowsMessage.textContent = error.message;
      windowsMessage.className = 'message error';
    }
  }
}

async function windowsAction(action) {
  if (vpnBusy || !lastVpnState || !windowsReady) return;
  const epoch = windowsEpoch;
  setVpnBusy(true); renderWindowsDevices(); setWindowsLink(null);
  windowsMessage.textContent = t('windowsWorking'); windowsMessage.className = 'message';
  try {
    await action();
    if (epoch === windowsEpoch) windowsMessage.className = 'message success';
  } catch (error) {
    if (epoch === windowsEpoch) {
      windowsMessage.textContent = error.message;
      windowsMessage.className = 'message error';
    }
  } finally {
    setVpnBusy(false); renderWindowsDevices();
    if (epoch === windowsEpoch) await loadWindowsDevices();
  }
}

windowsName.addEventListener('invalid', () => {
  if (!windowsName.value.trim()) windowsName.setCustomValidity(t('windowsNameRequired'));
});
windowsName.addEventListener('input', () => windowsName.setCustomValidity(''));

windowsForm.addEventListener('submit', event => {
  event.preventDefault();
  const name = windowsName.value.trim();
  if (!name) {
    windowsName.setCustomValidity(t('windowsNameRequired'));
    windowsName.reportValidity();
    return;
  }
  if (!windowsRequestId) windowsRequestId = crypto.randomUUID();
  windowsAction(async () => {
    const data = await apiRequest('/windows/devices', {
      method:'POST', body:JSON.stringify({requestId:windowsRequestId,name,language:currentLanguage})
    });
    setWindowsLink(data.profileUrl);
    windowsRequestId = null; windowsName.value = '';
    windowsMessage.textContent = t('windowsReady');
  });
});

document.getElementById('windowsCopyButton').addEventListener('click', async () => {
  if (!windowsProfileUrl) return;
  try { await copyText(windowsProfileUrl); windowsMessage.textContent = t('profileLinkCopied'); }
  catch { windowsMessage.textContent = t('profileShareFailed'); }
});

document.getElementById('windowsShareButton').addEventListener('click', async () => {
  if (!windowsProfileUrl) return;
  try {
    if (navigator.share) await navigator.share({title:'TOLF VPN — Windows',url:windowsProfileUrl});
    else { await copyText(windowsProfileUrl); windowsMessage.textContent = t('profileLinkCopied'); }
  } catch (error) {
    if (error.name !== 'AbortError') windowsMessage.textContent = t('profileShareFailed');
  }
});

(async () => {
  try {
    const capabilities = await apiRequest('/windows/capabilities', {method:'GET',cache:'no-store'});
    if (capabilities.version !== '1.0' || !capabilities.servers.includes('riga')) throw new Error('Windows unavailable');
    windowsReady = true;
    document.getElementById('platformWindows').classList.remove('hidden');
    renderWindowsDevices();
    if (currentPlatform === 'windows') await loadWindowsDevices();
  } catch {
    // Do not expose creation controls before the server supports independent devices.
    if (currentPlatform === 'windows') setPlatform('ios');
  }
})();
