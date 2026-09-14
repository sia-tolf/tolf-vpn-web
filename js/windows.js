let windowsDevices = [];
let expandedWindowsDevice = null;
let windowsEpoch = 0;
let windowsRequestId = null;
const windowsProfileLinks = new Map();
let windowsReady = false;
let windowsAdding = false;
const windowsList = document.getElementById('windowsDeviceList');
const windowsMessage = document.getElementById('windowsMessage');
const windowsForm = document.getElementById('windowsCreateForm');
const windowsName = document.getElementById('windowsDeviceName');
const windowsServer = document.getElementById('windowsDeviceServer');

function clearWindowsDevices() {
  windowsEpoch++;
  windowsDevices = [];
  expandedWindowsDevice = null;
  windowsRequestId = null;
  windowsName.value = '';
  windowsAdding = false;
  windowsMessage.textContent = '';
  windowsProfileLinks.clear();
  renderWindowsDevices();
}

function appendWindowsDelivery(card, device, actions) {
  const url = windowsProfileLinks.get(device.id);
  if (device.state !== 'active') return;
  const delivery = document.createElement('div');
  delivery.className = 'windows-device-delivery';
  const feedback = document.createElement('p');
  feedback.className = 'message';
  feedback.setAttribute('role', 'status');
  feedback.setAttribute('aria-live', 'polite');
  const copy = document.createElement('button');
  copy.type = 'button'; copy.className = 'windows-copy-button';
  copy.textContent = t('windowsCopy'); copy.disabled = vpnBusy || !url;
  copy.addEventListener('click', async () => {
    try { await copyText(url); feedback.textContent = t('profileLinkCopied'); }
    catch { feedback.textContent = t('profileShareFailed'); }
  });
  actions.append(copy);
  if (url && /Windows NT/i.test(navigator.userAgent || '')) {
    const open = document.createElement('a');
    open.className = 'button-link primary windows-device-open';
    open.href = url; open.target = '_blank'; open.rel = 'noopener noreferrer';
    open.textContent = t('windowsOpen'); delivery.append(open);
  }
  if (delivery.childElementCount) card.append(delivery);
  card.append(feedback);
}

function renderWindowsDevices() {
  if (windowsName.validity && windowsName.validity.customError) {
    windowsName.setCustomValidity(t('windowsNameRequired'));
  }
  document.getElementById("windowsDevicesHeading").classList.toggle("hidden", windowsDevices.length === 0);
  windowsList.replaceChildren();
  for (const device of windowsDevices) {
    const card = document.createElement('details');
    card.className = 'windows-device vpn-overview-card';
    card.name = 'windows-computers';
    card.open = expandedWindowsDevice === device.id;
    const name = document.createElement('summary'); name.textContent = device.name;
    const body = document.createElement('div'); body.className = 'windows-device-body';
    card.addEventListener('toggle', () => {
      if (!card.isConnected) return;
      if (card.open) {
        expandedWindowsDevice = device.id;
        for (const other of windowsList.children) {
          if (other !== card) other.open = false;
        }
      } else if (expandedWindowsDevice === device.id) {
        expandedWindowsDevice = null;
      }
    });
    const user = document.createElement('p');
    user.textContent = device.username || t('windowsPreparing');
    user.className = 'windows-device-username';
    const actions = document.createElement('div'); actions.className = 'actions windows-device-links';
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
    remove.className = 'danger windows-device-delete'; remove.textContent = t('windowsDelete'); remove.disabled = vpnBusy;
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
    actions.append(download); body.append(user, actions);
    appendWindowsDelivery(body, device, actions);
    body.append(remove);
    card.append(name, body);
    windowsList.append(card);
  }
  windowsForm.classList.toggle('hidden', !windowsAdding);
  document.getElementById('windowsStartActions').classList.toggle('hidden', windowsAdding);
  document.getElementById('windowsAddButton').setAttribute('aria-expanded', String(windowsAdding));
  document.getElementById('windowsAddButton').disabled = vpnBusy || !windowsReady;
  document.getElementById('windowsCancelButton').disabled = vpnBusy;
  document.getElementById('windowsCreateButton').disabled = vpnBusy || !windowsReady;
  windowsName.disabled = vpnBusy;
  windowsServer.disabled = vpnBusy;
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
    if (!activeIds.has(expandedWindowsDevice)) expandedWindowsDevice = null;
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

document.getElementById('windowsAddButton').addEventListener('click', () => {
  if (vpnBusy || !windowsReady || !lastVpnState) return;
  windowsServer.value = 'riga';
  windowsAdding = true;
  renderWindowsDevices();
  windowsName.focus();
});
document.getElementById('windowsCancelButton').addEventListener('click', () => {
  if (vpnBusy) return;
  windowsAdding = false;
  windowsName.setCustomValidity('');
  renderWindowsDevices();
  document.getElementById('windowsAddButton').focus();
});

windowsName.addEventListener('invalid', () => {
  if (!windowsName.value.trim()) windowsName.setCustomValidity(t('windowsNameRequired'));
});
windowsName.addEventListener('input', () => windowsName.setCustomValidity(''));

windowsForm.addEventListener('submit', event => {
  event.preventDefault();
  if (!windowsAdding || vpnBusy || !windowsReady || !lastVpnState) return;
  if (windowsServer.value !== 'riga') return;
  const name = windowsName.value.trim();
  if (!name) {
    windowsName.setCustomValidity(t('windowsNameRequired'));
    windowsName.reportValidity();
    return;
  }
  if (!windowsRequestId) windowsRequestId = crypto.randomUUID();
  windowsAction(async epoch => {
    const data = await apiRequest('/windows/devices', {
      method:'POST', body:JSON.stringify({requestId:windowsRequestId,name,server:windowsServer.value,language:currentLanguage})
    });
    if (epoch !== windowsEpoch) return;
    windowsProfileLinks.set(data.device.id, data.profileUrl);
    expandedWindowsDevice = data.device.id;
    windowsRequestId = null; windowsName.value = '';
    windowsAdding = false;
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
