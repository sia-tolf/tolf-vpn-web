let windowsDevices = [];
let windowsEpoch = 0;
let windowsRequestId = null;
const windowsProfileLinks = new Map();
let windowsReady = false;
const windowsList = document.getElementById('windowsDeviceList');
const windowsMessage = document.getElementById('windowsMessage');
const windowsForm = document.getElementById('windowsCreateForm');
const windowsName = document.getElementById('windowsDeviceName');

function clearWindowsDevices() {
  windowsEpoch++;
  windowsDevices = [];
  windowsRequestId = null;
  windowsName.value = '';
  windowsMessage.textContent = '';
  windowsProfileLinks.clear();
  renderWindowsDevices();
}

function appendWindowsDelivery(card, device) {
  const url = windowsProfileLinks.get(device.id);
  if (!url || device.state !== 'active') return;
  const delivery = document.createElement('div');
  delivery.className = 'windows-device-delivery';
  const feedback = document.createElement('p');
  feedback.className = 'message';
  feedback.setAttribute('role', 'status');
  feedback.setAttribute('aria-live', 'polite');
  const copy = document.createElement('button');
  copy.type = 'button'; copy.className = 'windows-copy-button';
  copy.textContent = t('windowsCopy'); copy.disabled = vpnBusy;
  copy.addEventListener('click', async () => {
    try { await copyText(url); feedback.textContent = t('profileLinkCopied'); }
    catch { feedback.textContent = t('profileShareFailed'); }
  });
  const share = document.createElement('button');
  share.type = 'button'; share.className = 'constructive';
  share.textContent = t('windowsShare'); share.disabled = vpnBusy;
  share.addEventListener('click', async () => {
    try {
      if (navigator.share) await navigator.share({title:'TOLF VPN — ' + device.name, url});
      else { await copyText(url); feedback.textContent = t('profileLinkCopied'); }
    } catch (error) {
      if (error.name !== 'AbortError') feedback.textContent = t('profileShareFailed');
    }
  });
  delivery.append(copy, share);
  if (/Windows NT/i.test(navigator.userAgent || '')) {
    const open = document.createElement('a');
    open.className = 'button-link primary windows-device-open';
    open.href = url; open.target = '_blank'; open.rel = 'noopener noreferrer';
    open.textContent = t('windowsOpen'); delivery.append(open);
  }
  card.append(delivery, feedback);
}

function renderWindowsDevices() {
  if (windowsName.validity && windowsName.validity.customError) {
    windowsName.setCustomValidity(t('windowsNameRequired'));
  }
  document.getElementById("windowsDevicesHeading").classList.toggle("hidden", windowsDevices.length === 0);
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
    download.addEventListener('click', () => windowsAction(async epoch => {
      const data = await apiRequest(`/windows/devices/${encodeURIComponent(device.id)}/profile`, {
        method: 'POST', body: JSON.stringify({language: currentLanguage})
      });
      if (epoch !== windowsEpoch) return;
      windowsProfileLinks.set(device.id, data.profileUrl);
      windowsRequestId = null;
      windowsMessage.textContent = '';
    }));
    const remove = document.createElement('button'); remove.type = 'button';
    remove.className = 'danger'; remove.textContent = t('windowsDelete'); remove.disabled = vpnBusy;
    remove.addEventListener('click', () => {
      if (!window.confirm(t('windowsDeleteConfirm', {name: device.name}))) return;
      windowsAction(async epoch => {
        await apiRequest(`/windows/devices/${encodeURIComponent(device.id)}/delete`, {method:'POST',body:'{}'});
        windowsRequestId = null;
        if (epoch !== windowsEpoch) return;
        windowsProfileLinks.delete(device.id);
        windowsMessage.textContent = t('windowsDeleted');
      });
    });
    actions.append(download, remove); card.append(name, user, actions);
    appendWindowsDelivery(card, device);
    windowsList.append(card);
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
    const activeIds = new Set(windowsDevices.map(device => device.id));
    for (const id of windowsProfileLinks.keys()) {
      if (!activeIds.has(id)) windowsProfileLinks.delete(id);
    }
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
  setVpnBusy(true); renderWindowsDevices();
  windowsMessage.textContent = t('windowsWorking'); windowsMessage.className = 'message';
  try {
    await action(epoch);
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
  windowsAction(async epoch => {
    const data = await apiRequest('/windows/devices', {
      method:'POST', body:JSON.stringify({requestId:windowsRequestId,name,language:currentLanguage})
    });
    if (epoch !== windowsEpoch) return;
    windowsProfileLinks.set(data.device.id, data.profileUrl);
    windowsRequestId = null; windowsName.value = '';
    windowsMessage.textContent = '';
  });
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
