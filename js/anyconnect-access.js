// Personal access. Import passwords and bearer links live only in page memory.
(() => {
  const root = document.getElementById("anyConnectAccess");
  if (!root) return;
  const GUIDE = "https://www.cisco.com/c/en/us/td/docs/security/vpn_client/anyconnect/Cisco-Secure-Client-5/admin/guide/cisco-secure-client-admin-guide-new/ac-on-mobile-devices-intro/t_automate_anyconnect_actions_using_the_uri_handler.html";
  const COPY = {
    ru: {
      title: "Доступ AnyConnect", device: "Устройство", newDevice: "Название нового устройства",
      create: "Создать доступ", additional: "Создать дополнительный доступ", cancel: "Отмена", resume: "Завершить выдачу", refresh: "Повторить попытку", choose: "Выберите устройство",
      install: "Установите Cisco Secure Client (AnyConnect).", app: "Установить Cisco Secure Client",
      control: "Перед импортом сертификата откройте настройки приложения Cisco Secure Client и выберите External Control → Prompt. Затем вернитесь сюда и нажмите «Импортировать в AnyConnect».",
      controlReminder: "Перед нажатием «Добавить соединение в AnyConnect» проверьте, что в приложении Cisco Secure Client выбрано External Control → Prompt.",
      enableTitle: "Включите VPN",
      certificate: "Импортируйте сертификат", prepare: "Получить сертификат",
      connectionLinkHelp: "После добавления соединения получите сертификат и импортируйте его в AnyConnect.",
      import: "Импортировать в AnyConnect", download: "Скачать сертификат .p12", password: "Пароль импорта",
      copy: "Скопировать пароль", copied: "Пароль скопирован",
      expires: "Ссылка одноразовая и действует 10 минут. Пароль понадобится при импорте. После обновления страницы получите новую ссылку.",
      expired: "Ссылка истекла. Получите новый сертификат и ссылки.",
      manual: "Для ручного импорта сохраните файл .p12. На iPhone и iPad откройте его в «Файлах» и через «Поделиться» передайте в Cisco Secure Client. Используйте указанный пароль импорта.",
      windows: "Скачайте файл .p12. Откройте его и импортируйте с указанным паролем в хранилище сертификатов текущего пользователя → Личное.",
      connect: "Добавьте соединение", add: "Добавить соединение в AnyConnect",
      return: "Сначала добавьте соединение в AnyConnect. Затем вернитесь сюда и импортируйте сертификат в шаге 4. VPN включайте после импорта сертификата.",
      host: "Для ручного добавления: адрес oc.tolf.is:4443. После импорта сертификата в шаге 4 выберите его в настройках этого соединения.",
      enable: "Включите VPN в приложении. Если предлагается группа, оставьте группу по умолчанию. Вернитесь на сайт: зелёная точка появится после подтверждения сессии выбранного устройства. Маршрутизацию меняйте здесь.",
      ready: "Доступ готов", pending: "Выдача не завершена", revoking: "Отзыв выполняется",
      unavailable: "Выдача пока недоступна. Обновите после активации сервера.", loading: "Загрузка…",
      failed: "Не удалось выполнить действие. Повторите попытку.",
      revoke: "Отозвать доступ", confirm: "Отозвать доступ этого устройства? Его VPN-соединение будет отключено.",
      revoked: "Доступ отозван.", revokePending: "Отзыв принят. Сервер завершит отключение после восстановления связи.",
      separate: "Создавайте отдельный доступ для каждого устройства. Сертификат и пароль предназначены только для вас.",
      docs: "Инструкция Cisco", name: "Мой iPad"
    },
    en: {
      title: "AnyConnect access", device: "Device", newDevice: "New device name",
      create: "Create access", additional: "Create additional access", cancel: "Cancel", resume: "Complete issuance", refresh: "Try again", choose: "Choose a device",
      install: "Install Cisco Secure Client (AnyConnect).", app: "Install Cisco Secure Client",
      control: "Before importing the certificate, open Cisco Secure Client settings and select External Control → Prompt. Then return here and select “Import into AnyConnect”.",
      controlReminder: "Before selecting “Add connection in AnyConnect”, check that Cisco Secure Client has External Control → Prompt selected.",
      enableTitle: "Enable VPN",
      certificate: "Import the certificate", prepare: "Get certificate",
      connectionLinkHelp: "After adding the connection, get the certificate and import it into AnyConnect.",
      import: "Import into AnyConnect", download: "Download .p12 certificate", password: "Import password",
      copy: "Copy password", copied: "Password copied",
      expires: "The link works once and expires in 10 minutes. Use this password during import. After reloading the page, get a new link.",
      expired: "The link expired. Get a new certificate and links.",
      manual: "For manual import, save the .p12 file. On iPhone and iPad, open it in Files and use Share to send it to Cisco Secure Client. Use the displayed import password.",
      windows: "Download the .p12 file. Open it and import it with this password into Current User → Personal certificate store.",
      connect: "Add the connection", add: "Add connection in AnyConnect",
      return: "First add the connection in AnyConnect. Then return here and import the certificate in step 4. Enable VPN after importing the certificate.",
      host: "For manual setup: server oc.tolf.is:4443. After importing the certificate in step 4, select it in this connection’s settings.",
      enable: "Enable VPN in the app. Keep the default group if asked. Return here: the green dot appears after this device’s session is confirmed. Change routing here.",
      ready: "Access ready", pending: "Issuance incomplete", revoking: "Revocation in progress",
      unavailable: "Issuance is unavailable. Refresh after server activation.", loading: "Loading…",
      failed: "The action failed. Refresh and try again.",
      revoke: "Revoke access", confirm: "Revoke this device’s access? Its VPN connection will be disconnected.",
      revoked: "Access revoked.", revokePending: "Revocation accepted. Disconnection will complete when server connectivity returns.",
      separate: "Create separate access for each device. Keep the certificate and password private.",
      docs: "Cisco instructions", name: "My device"
    },
    lv: {
      title: "AnyConnect piekļuve", device: "Ierīce", newDevice: "Jaunās ierīces nosaukums",
      create: "Izveidot piekļuvi", additional: "Izveidot papildu piekļuvi", cancel: "Atcelt", resume: "Pabeigt izsniegšanu", refresh: "Mēģināt vēlreiz", choose: "Izvēlieties ierīci",
      install: "Instalējiet Cisco Secure Client (AnyConnect).", app: "Instalēt Cisco Secure Client",
      control: "Pirms sertifikāta importēšanas atveriet Cisco Secure Client iestatījumus un izvēlieties External Control → Prompt. Pēc tam atgriezieties šeit un nospiediet “Importēt AnyConnect”.",
      controlReminder: "Pirms nospiežat “Pievienot savienojumu AnyConnect”, pārbaudiet, vai Cisco Secure Client ir izvēlēts External Control → Prompt.",
      enableTitle: "Ieslēdziet VPN",
      certificate: "Importējiet sertifikātu", prepare: "Saņemt sertifikātu",
      connectionLinkHelp: "Pēc savienojuma pievienošanas saņemiet sertifikātu un importējiet to AnyConnect.",
      import: "Importēt AnyConnect", download: "Lejupielādēt .p12 sertifikātu", password: "Importēšanas parole",
      copy: "Kopēt paroli", copied: "Parole nokopēta",
      expires: "Saite ir vienreizēja un derīga 10 minūtes. Importēšanai izmantojiet šo paroli. Pēc lapas pārlādes saņemiet jaunu saiti.",
      expired: "Saites derīgums beidzies. Saņemiet jaunu sertifikātu un saites.",
      manual: "Manuālai importēšanai saglabājiet .p12 failu. iPhone un iPad atveriet to lietotnē Files un ar Share nosūtiet uz Cisco Secure Client. Izmantojiet norādīto importēšanas paroli.",
      windows: "Lejupielādējiet .p12 failu. Atveriet to un importējiet ar norādīto paroli pašreizējā lietotāja personīgajā sertifikātu krātuvē.",
      connect: "Pievienojiet savienojumu", add: "Pievienot savienojumu AnyConnect",
      return: "Vispirms pievienojiet savienojumu AnyConnect. Pēc tam atgriezieties šeit un importējiet sertifikātu 4. solī. Ieslēdziet VPN pēc sertifikāta importēšanas.",
      host: "Manuālai pievienošanai: serveris oc.tolf.is:4443. Pēc sertifikāta importēšanas 4. solī izvēlieties to šī savienojuma iestatījumos.",
      enable: "Ieslēdziet VPN lietotnē. Ja tiek prasīta grupa, atstājiet noklusējuma grupu. Atgriezieties vietnē: zaļais punkts parādīsies pēc šīs ierīces sesijas apstiprināšanas. Maršrutēšanu mainiet šeit.",
      ready: "Piekļuve gatava", pending: "Izsniegšana nav pabeigta", revoking: "Notiek atsaukšana",
      unavailable: "Izsniegšana nav pieejama. Atjauniniet pēc servera aktivizēšanas.", loading: "Ielāde…",
      failed: "Darbība neizdevās. Atjauniniet un mēģiniet vēlreiz.",
      revoke: "Atsaukt piekļuvi", confirm: "Atsaukt šīs ierīces piekļuvi? VPN savienojums tiks pārtraukts.",
      revoked: "Piekļuve atsaukta.", revokePending: "Atsaukšana pieņemta. Savienojums tiks pārtraukts pēc saziņas ar serveri atjaunošanas.",
      separate: "Izveidojiet atsevišķu piekļuvi katrai ierīcei. Sertifikāts un parole paredzēti tikai jums.",
      docs: "Cisco instrukcija", name: "Mana ierīce"
    }
  };
  let account = null, devices = [], selectedId = null, capabilities = null;
  let grant = null, busy = false, loading = false, epoch = 0, message = "", error = false;
  let deviceName = "", creationRequest = null, addingDevice = false;
  let copyNotice = null, copyNoticeTimer = null;
  let downloadedPackage = null;
  const copy = () => COPY[document.documentElement.lang] || COPY.en;
  const selected = () => devices.find(d => d.id === selectedId && d.state === "active") || null;
  window.ocAccess = { selected, accountUsername: () => account?.vpn?.username || "" };
  const path = id => "/oc/access/devices/" + encodeURIComponent(id);
  function connectionUri(d) {
    const name = "TOLF " + Array.from(d.label).slice(0,10).join("") + " " + d.id.replaceAll("-", "").slice(-8);
    const params = {name, host:"oc.tolf.is:4443", usecert:"true", certcommonname:d.username, netroam:"true"};
    return "anyconnect://create/?" + Object.entries(params).map(([key,value]) =>
      encodeURIComponent(key) + "=" + encodeURIComponent(value)).join("&");
  }
  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function button(text, action, primary = false) {
    const node = element("button", text, "oc-action " + (primary ? "primary" : "secondary"));
    node.type = "button"; node.disabled = busy || loading;
    node.addEventListener("click", action); return node;
  }
  function link(text, url, primary = false) {
    const node = element("a", text, "button-link oc-action " + (primary ? "primary" : "secondary"));
    node.href = url; node.referrerPolicy = "no-referrer";
    if (url.startsWith("https://") && !url.startsWith(API)) { node.target = "_blank"; node.rel = "noopener noreferrer"; }
    return node;
  }
  function choose(id) {
    selectedId = id; grant = null; clearCopyNotice(); clearDownloadedPackage();
    window.refreshAnyConnectTransport?.(); render();
  }
  function clearDownloadedPackage() {
    if (downloadedPackage) URL.revokeObjectURL(downloadedPackage.url);
    downloadedPackage = null;
  }
  async function downloadCertificate() {
    const currentGrant = grant;
    if (!currentGrant) return;
    await perform(async token => {
      if (!downloadedPackage || downloadedPackage.grant !== currentGrant) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 20000);
        let bytes;
        try {
          const response = await fetch(currentGrant.certificateUrl, {cache:"no-store", credentials:"omit", signal:controller.signal});
          if (!response.ok) throw new Error("Certificate download failed");
          bytes = await response.arrayBuffer();
        } finally { clearTimeout(timer); }
        if (token !== epoch || currentGrant !== grant) return;
        clearDownloadedPackage();
        downloadedPackage = {grant:currentGrant, url:URL.createObjectURL(new Blob([bytes], {type:"application/octet-stream"}))};
      }
      if (token !== epoch || currentGrant !== grant) return;
      const anchor = document.createElement("a");
      anchor.href = downloadedPackage.url;
      anchor.download = "TOLF-AnyConnect.p12";
      anchor.style.display = "none";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    });
  }
  function revokeDevice(d) {
    if (!window.confirm(copy().confirm)) return;
    perform(async token => {
      const result = await apiRequest(path(d.id) + "/revoke", {method:"POST", timeoutMs:70000});
      if (token !== epoch) return;
      grant = null; clearCopyNotice(); clearDownloadedPackage(); await refresh();
      if (token === epoch) message = result.device?.state === "revoked" ? copy().revoked : copy().revokePending;
    });
  }
  function clearCopyNotice() {
    clearTimeout(copyNoticeTimer);
    copyNotice = null;
  }
  async function copyPassword() {
    const token = epoch, currentGrant = grant;
    if (!currentGrant) return;
    clearCopyNotice();
    try {
      await copyText(currentGrant.password);
      if (token !== epoch || currentGrant !== grant) return;
      copyNotice = "copied"; render();
      copyNoticeTimer = setTimeout(() => { copyNotice = null; render(); }, 2000);
    } catch {
      if (token === epoch && currentGrant === grant) { copyNotice = "failed"; render(); }
    }
  }
  async function refresh() {
    if (!account) return;
    const token = epoch;
    loading = true; render();
    const results = await Promise.allSettled([
      apiRequest("/oc/access/capabilities", { cache: "no-store", timeoutMs: 30000 }),
      apiRequest("/oc/access/devices", { cache: "no-store", timeoutMs: 30000 })
    ]);
    if (token !== epoch) return;
    capabilities = results[0].status === "fulfilled" ? results[0].value : null;
    if (results[1].status === "fulfilled") {
      devices = results[1].value.devices.filter(d => d.state !== "revoked");
      if (!devices.some(d => d.id === selectedId)) {
        selectedId = devices.find(d => d.state === "active")?.id || devices[0]?.id || null;
        grant = null;
        clearDownloadedPackage();
      }
    } else { message = copy().failed; error = true; }
    loading = false;
    window.refreshAnyConnectTransport?.(); render();
  }
  async function perform(action) {
    if (busy || loading || !account) return;
    const token = epoch;
    busy = true; message = ""; error = false; render();
    try { await action(token); }
    catch { if (token === epoch) { await refresh(); message = copy().failed; error = true; } }
    finally { if (token === epoch) { busy = false; render(); } }
  }
  async function create(requestId, label, token) {
    const result = await apiRequest("/oc/access/devices", {
      method: "POST", body: JSON.stringify({ requestId, label }), timeoutMs: 30000
    });
    if (token !== epoch) return;
    creationRequest = null; deviceName = ""; addingDevice = false;
    devices = devices.filter(d => d.id !== result.device.id).concat(result.device);
    choose(result.device.id);
    message = copy().ready;
  }
  function render() {
    root.replaceChildren();
    if (!account) return;
    const c = copy(), mobile = currentPlatform !== "windows";
    root.append(element("h3", c.title), element("p", c.separate, "oc-note"));
    root.append(element("h4", "1. " + c.install));
    const appUrl = currentPlatform === "ios" ? "https://apps.apple.com/app/id1135064690" :
      currentPlatform === "android" ? "https://play.google.com/store/apps/details?id=com.cisco.anyconnect.vpn.android.avf" :
      "https://www.cisco.com/c/en/us/support/security/secure-client-5/model.html";
    root.append(link(c.app, appUrl));
    root.append(element("h4", "2. " + c.device));
    if (devices.length) {
      const label = element("label", c.device); label.setAttribute("for", "ocDeviceSelect"); root.append(label);
      const row = element("div", null, "oc-device-row");
      const select = element("select"); select.id = "ocDeviceSelect"; select.setAttribute("aria-label", c.device);
      select.disabled = busy || loading;
      for (const d of devices) {
        const opt = element("option", d.label + " — " + (d.state === "active" ? c.ready : d.state === "pending" ? c.pending : c.revoking));
        opt.value = d.id; opt.selected = d.id === selectedId; select.append(opt);
      }
      select.addEventListener("change", () => choose(select.value)); row.append(select);
      const current = devices.find(d => d.id === selectedId);
      if (current) {
        const revoke = button(c.revoke, () => revokeDevice(current));
        revoke.className = "oc-action danger";
        row.append(revoke);
      }
      root.append(row);
    }
    const pending = devices.find(d => d.id === selectedId && d.state === "pending");
    if (pending) root.append(button(c.resume, () => perform(token => create(pending.request_id, pending.label, token)), true));
    if (devices.length && !addingDevice) {
      const actions = element("div", null, "oc-actions");
      actions.append(button(c.additional, () => { addingDevice = true; render(); }));
      root.append(actions);
    }
    if (!devices.length || addingDevice) {
    root.append(element("label", c.newDevice));
    const name = element("input"); name.type = "text"; name.maxLength = 80; name.value = deviceName;
    name.placeholder = c.name; name.setAttribute("aria-label", c.newDevice); name.disabled = busy || loading;
    name.addEventListener("input", () => {
      deviceName = name.value; creationRequest = null;
      createButton.disabled = busy || loading || !deviceName.trim() || capabilities?.issuance !== true;
    }); root.append(name);
    const createButton = button(c.create, () => perform(token => {
      if (!deviceName.trim()) { name.focus(); return; }
      creationRequest ||= crypto.randomUUID();
      return create(creationRequest, deviceName.trim(), token);
    }), true);
    createButton.disabled ||= capabilities?.issuance !== true || !deviceName.trim();
    const createActions = element("div", null, "oc-actions");
    createActions.append(createButton);
    if (devices.length) createActions.append(button(c.cancel, () => {
      addingDevice = false; deviceName = ""; creationRequest = null; render();
    }));
    root.append(createActions);
    }
    if (!capabilities?.issuance) root.append(element("p", loading ? c.loading : c.unavailable, "oc-note"));
    const d = selected();
    if (d) {
      const steps = element("div", null, "oc-steps");
      const connect = element("section", null, "oc-step"); connect.append(element("h4", "3. " + c.connect), element("p", c.return));
      if (mobile) connect.append(element("p", c.controlReminder), link(c.add, connectionUri(d), true));
      connect.append(element("p", c.host)); steps.append(connect);
      const cert = element("section", null, "oc-step"); cert.append(element("h4", "4. " + c.certificate));
      const prepare = button(c.prepare, () => perform(async token => {
        const id = d.id;
        const result = await apiRequest(path(id) + "/import", { method: "POST", timeoutMs: 30000 });
        if (token === epoch && selectedId === id) { grant = result; clearCopyNotice(); clearDownloadedPackage(); }
      }), true);
      prepare.className += " oc-prepare";
      prepare.disabled ||= capabilities?.issuance !== true; cert.append(prepare, element("p", c.connectionLinkHelp, "oc-note"));
      if (grant?.deviceId === d.id) {
        cert.append(element("p", c.password));
        const passwordRow = element("div", null, "oc-password-row");
        passwordRow.append(element("span", grant.password, "oc-secret"));
        const copyButton = button("", copyPassword);
        copyButton.className = "oc-copy";
        copyButton.setAttribute("aria-label", c.copy);
        copyButton.title = c.copy;
        const glyph = element("span", null, "oc-copy-glyph");
        glyph.setAttribute("aria-hidden", "true"); copyButton.append(glyph);
        const copyControl = element("span", null, "oc-copy-control");
        copyControl.append(copyButton);
        if (copyNotice) {
          const feedback = element("span", copyNotice === "copied" ? c.copied : c.failed, "oc-copy-feedback");
          feedback.setAttribute("role", "status");
          feedback.setAttribute("aria-live", "polite");
          copyControl.append(feedback);
        }
        passwordRow.append(copyControl);
        cert.append(passwordRow);
        if (mobile) cert.append(element("p", c.control));
        const importActions = element("div", null, "oc-actions oc-import-actions");
        if (mobile) importActions.append(link(c.import, grant.importUri, true));
        importActions.append(button(c.download, downloadCertificate));
        cert.append(importActions, element("p", c.expires, "oc-note"));
      }
      cert.append(element("p", mobile ? c.manual : c.windows, "oc-note")); steps.append(cert);
      const enable = element("section", null, "oc-step");
      enable.append(element("h4", "5. " + c.enableTitle), element("p", c.enable));
      steps.append(enable); root.append(steps);
    }
    const status = element("p", message, "oc-message" + (error ? " oc-error" : ""));
    status.setAttribute("role", "status"); status.setAttribute("aria-live", "polite"); root.append(status);
    if (error || (!loading && capabilities?.issuance !== true)) {
      root.append(button(c.refresh, () => { message = ""; error = false; refresh(); }));
    }
    root.append(link(c.docs, GUIDE));
  }
  window.setAnyConnectAccount = data => {
    if (account?.userId === data?.userId && account) {
      account = data;
      window.renderVpnProtocol?.();
      return;
    }
    epoch++; account = data?.authenticated ? data : null;
    clearCopyNotice();
    clearDownloadedPackage();
    devices = []; selectedId = null; grant = null; capabilities = null;
    deviceName = ""; creationRequest = null; addingDevice = false; busy = false; loading = false; message = ""; error = false;
    window.refreshAnyConnectTransport?.(); render();
    if (account) refresh();
  };
  for (const event of ["vpntransportchange", "vpnplatformchange"]) window.addEventListener(event, render);
  new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  setInterval(() => {
    if (grant && Date.parse(grant.expiresAt) <= Date.now()) { grant = null; clearCopyNotice(); clearDownloadedPackage(); message = copy().expired; render(); }
  }, 1000);
  window.addEventListener("pagehide", () => { grant = null; clearCopyNotice(); clearDownloadedPackage(); });
  window.addEventListener("pageshow", render);
  window.setAnyConnectAccount(window.tolfAccountState || null);
})();
