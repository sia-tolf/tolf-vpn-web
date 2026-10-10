// Personal access. Import passwords and bearer links live only in page memory.
(() => {
  const root = document.getElementById("anyConnectAccess");
  if (!root) return;
  // Keep the existing controls and their policy handlers when rebuilding the steps.
  const routingControls = document.getElementById("anyConnectModeRow");
  if (routingControls) {
    routingControls.classList.add("oc-device-routing");
    root.append(routingControls);
  }
  const GUIDE = "https://www.cisco.com/c/en/us/td/docs/security/vpn_client/anyconnect/Cisco-Secure-Client-5/admin/guide/cisco-secure-client-admin-guide-new/ac-on-mobile-devices-intro/t_automate_anyconnect_actions_using_the_uri_handler.html";
  const COPY = {
    ru: {
      title: "Доступ AnyConnect", device: "Устройство", newDevice: "Название нового устройства",
      create: "Создать доступ", additional: "Создать дополнительный доступ", cancel: "Отмена", resume: "Завершить выдачу", refresh: "Повторить попытку", choose: "Выберите устройство",
      install: "Установите Cisco Secure Client (AnyConnect).", app: "Установить Cisco Secure Client",
      control: "Перед импортом сертификата откройте настройки приложения Cisco Secure Client и выберите External Control → Prompt. Затем вернитесь сюда и нажмите «Импортировать в AnyConnect».",
      controlReminder: "Перед нажатием «Добавить в AnyConnect» проверьте, что в приложении Cisco Secure Client выбрано External Control → Prompt.",
      enableTitle: "Включите VPN",
      certificate: "Получите сертификат для импорта в AnyConnect", prepare: "Получить сертификат",
      passwordHelp: "Этот пароль понадобится при импорте данного сертификата в приложение Cisco Secure Client (AnyConnect).",
      connectionLinkHelp: "После добавления соединения получите сертификат и импортируйте его в AnyConnect.",
      import: "Импортировать в AnyConnect", download: "Скачать сертификат .p12", password: "Пароль импорта",
      copy: "Скопировать пароль", copied: "Пароль скопирован",
      expires: "Ссылка одноразовая и действует 2 часа. Пароль понадобится при импорте. После обновления страницы получите новую ссылку.",
      expired: "Ссылка истекла. Получите новый сертификат и ссылки.",
      manual: "Для ручного импорта сохраните файл .p12. На iPhone и iPad откройте его в «Файлах» и через «Поделиться» передайте в Cisco Secure Client. Используйте указанный пароль импорта.",
      windows: "Скачайте файл .p12. Откройте его и импортируйте с указанным паролем в хранилище сертификатов текущего пользователя → Личное.",
      connect: "Добавьте соединение", add: "Добавить в AnyConnect",
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
      controlReminder: "Before selecting “Add to AnyConnect”, check that Cisco Secure Client has External Control → Prompt selected.",
      enableTitle: "Enable VPN",
      certificate: "Get the certificate for import into AnyConnect", prepare: "Get certificate",
      passwordHelp: "Use this password when importing this certificate into Cisco Secure Client (AnyConnect).",
      connectionLinkHelp: "After adding the connection, get the certificate and import it into AnyConnect.",
      import: "Import into AnyConnect", download: "Download .p12 certificate", password: "Import password",
      copy: "Copy password", copied: "Password copied",
      expires: "The link works once and expires in 2 hours. Use this password during import. After reloading the page, get a new link.",
      expired: "The link expired. Get a new certificate and links.",
      manual: "For manual import, save the .p12 file. On iPhone and iPad, open it in Files and use Share to send it to Cisco Secure Client. Use the displayed import password.",
      windows: "Download the .p12 file. Open it and import it with this password into Current User → Personal certificate store.",
      connect: "Add the connection", add: "Add to AnyConnect",
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
      controlReminder: "Pirms nospiežat “Pievienot AnyConnect”, pārbaudiet, vai Cisco Secure Client ir izvēlēts External Control → Prompt.",
      enableTitle: "Ieslēdziet VPN",
      certificate: "Saņemiet sertifikātu importēšanai AnyConnect", prepare: "Saņemt sertifikātu",
      passwordHelp: "Šī parole būs vajadzīga, importējot šo sertifikātu lietotnē Cisco Secure Client (AnyConnect).",
      connectionLinkHelp: "Pēc savienojuma pievienošanas saņemiet sertifikātu un importējiet to AnyConnect.",
      import: "Importēt AnyConnect", download: "Lejupielādēt .p12 sertifikātu", password: "Importēšanas parole",
      copy: "Kopēt paroli", copied: "Parole nokopēta",
      expires: "Saite ir vienreizēja un derīga 2 stundas. Importēšanai izmantojiet šo paroli. Pēc lapas pārlādes saņemiet jaunu saiti.",
      expired: "Saites derīgums beidzies. Saņemiet jaunu sertifikātu un saites.",
      manual: "Manuālai importēšanai saglabājiet .p12 failu. iPhone un iPad atveriet to lietotnē Files un ar Share nosūtiet uz Cisco Secure Client. Izmantojiet norādīto importēšanas paroli.",
      windows: "Lejupielādējiet .p12 failu. Atveriet to un importējiet ar norādīto paroli pašreizējā lietotāja personīgajā sertifikātu krātuvē.",
      connect: "Pievienojiet savienojumu", add: "Pievienot AnyConnect",
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
  Object.assign(COPY.ru, {
    iosInstall: "Установить профиль AnyConnect",
    iosInstallHelp: "Одним MobileConfig устанавливаются соединение, сертификат и автоматическое подключение. После загрузки подтвердите установку в настройках iPhone или iPad.",
  });
  Object.assign(COPY.en, {
    iosInstall: "Install AnyConnect profile",
    iosInstallHelp: "One MobileConfig installs the connection, certificate and automatic On Demand. Confirm the profile in iPhone or iPad Settings.",
  });
  Object.assign(COPY.lv, {
    iosInstall: "Instalēt AnyConnect profilu",
    iosInstallHelp: "Viens MobileConfig instalē savienojumu, sertifikātu un automātisku pieslēgšanos. Apstipriniet profilu iPhone vai iPad iestatījumos.",
  });
  let account = null, devices = [], selectedId = null, capabilities = null;
  let grant = null, busy = false, loading = false, epoch = 0, message = "", error = false;
  let deviceName = "", creationRequest = null, addingDevice = false;
  let copyNotice = null, copyNoticeTimer = null;
  let downloadedPackage = null;
  let statusBadge = null;
  const incomingDevice = new URLSearchParams(window.location?.search || "").get("ocDevice");
  let setupDestination = null, transferNotice = "";
  let setupSteps = null;
  let confirmedDeviceId = null;
  let importedDeviceId = null;
  let ingressId = 'moscow';
  const INGRESS_COPY = {
    ru:{label:'Точка входа',moscow:'Москва',riga:'Рига',help:'Для Москвы и Риги используются разные соединения и один сертификат этого доступа. Чтобы сменить точку входа, выключите VPN в Cisco Secure Client, выберите другое соединение и включите VPN.'},
    en:{label:'Entry point',moscow:'Moscow',riga:'Riga',help:'Moscow and Riga use separate connections and the same access certificate. To switch entry points, disconnect VPN in Cisco Secure Client, select the other connection and reconnect.'},
    lv:{label:'Ieejas punkts',moscow:'Maskava',riga:'Rīga',help:'Maskavai un Rīgai ir atsevišķi savienojumi ar vienu šīs piekļuves sertifikātu. Lai mainītu ieejas punktu, Cisco Secure Client atvienojiet VPN, izvēlieties otru savienojumu un pievienojieties vēlreiz.'}
  };
  const ingressCopy = () => INGRESS_COPY[document.documentElement.lang] || INGRESS_COPY.en;
  const ingresses = () => (capabilities?.ingresses || [{id:'moscow',host:'oc.tolf.is:4443'}])
    .filter(item => item.id === 'moscow' && item.host === 'oc.tolf.is:4443' || item.id === 'riga' && item.host === 'oc-riga.tolf.is:443');
  const ingress = () => ingresses().find(item => item.id === ingressId) || ingresses()[0] || {id:'moscow',host:'oc.tolf.is:4443'};
  function selectIngress(id) {
    if (busy || loading || !ingresses().some(item => item.id === id) || ingressId === id) return;
    ingressId = id; confirmedDeviceId = null;
    render(); window.refreshAnyConnectIngress?.();
  }
  const CERTIFICATE_COPY = {
    ru:{already:"Сертификат уже импортирован", done:"✓ Сертификат уже импортирован", help:"Если сертификат этого доступа уже установлен в Cisco Secure Client, повторный импорт не нужен. Выберите его в настройках нового соединения."},
    en:{already:"Certificate already imported", done:"✓ Certificate already imported", help:"If this access certificate is already installed in Cisco Secure Client, no new import is needed. Select it in the new connection settings."},
    lv:{already:"Sertifikāts jau importēts", done:"✓ Sertifikāts jau importēts", help:"Ja šīs piekļuves sertifikāts jau ir instalēts Cisco Secure Client, atkārtota importēšana nav vajadzīga. Izvēlieties to jaunā savienojuma iestatījumos."}
  };
  const certificateCopy = () => CERTIFICATE_COPY[document.documentElement.lang] || CERTIFICATE_COPY.en;
  const STEP_COPY = {
    ru: {confirm:"Соединение добавлено", blocked:"Сначала добавьте соединение в AnyConnect и подтвердите завершение предыдущего шага."},
    en: {confirm:"Connection added", blocked:"First add the connection in AnyConnect and confirm completion of the previous step."},
    lv: {confirm:"Savienojums pievienots", blocked:"Vispirms pievienojiet savienojumu AnyConnect un apstipriniet iepriekšējā soļa pabeigšanu."}
  };
  const stepCopy = () => STEP_COPY[document.documentElement.lang] || STEP_COPY.en;
  const completedCopy = () => ({ru:{done:"✓ Соединение добавлено",again:"Добавить заново"},en:{done:"✓ Connection added",again:"Add again"},lv:{done:"✓ Savienojums pievienots",again:"Pievienot vēlreiz"}}[document.documentElement.lang] || {done:"✓ Connection added",again:"Add again"});
  let transferGrant = null, transferTimer = null;
  const TRANSFER_COPY = {
    ru: {create:"Создать ссылку для установки", help:"Отправьте ссылку получателю. Вход в аккаунт для установки не требуется.", expires:"Ссылка действует 24 часа и используется один раз для получения сертификата.", update:"Передача без входа станет доступна после обновления API на UK."},
    en: {create:"Create installation link", help:"Send this link to the recipient. No account sign-in is needed for installation.", expires:"The link lasts 24 hours and can be used once to obtain the certificate.", update:"Guest transfer requires the UK API update."},
    lv: {create:"Izveidot instalēšanas saiti", help:"Nosūtiet saiti saņēmējam. Instalēšanai nav jāpiesakās kontā.", expires:"Saite derīga 24 stundas un izmantojama vienu reizi sertifikāta saņemšanai.", update:"Pārsūtīšanai bez pieteikšanās nepieciešams UK API atjauninājums."}
  };
  const transferCopy = () => TRANSFER_COPY[document.documentElement.lang] || TRANSFER_COPY.en;
  const DELIVERY_COPY = {
    ru: {local:"Настроить на этом устройстве", remote:"Передать на другое устройство", help:"Откройте эту ссылку на нужном устройстве и войдите в тот же аккаунт TOLF. Будет выбран этот доступ. Затем добавьте соединение и импортируйте сертификат.", copy:"Скопировать ссылку", share:"Поделиться ссылкой", copied:"Ссылка скопирована", missing:"Этот доступ недоступен в текущем аккаунте. Войдите в аккаунт, в котором он создан."},
    en: {local:"Set up on this device", remote:"Transfer to another device", help:"Open this link on the target device and sign in to the same TOLF account. This access will be selected. Then add the connection and import the certificate.", copy:"Copy link", share:"Share link", copied:"Link copied", missing:"This access is unavailable in this account. Sign in to the account that created it."},
    lv: {local:"Iestatīt šajā ierīcē", remote:"Pārsūtīt uz citu ierīci", help:"Atveriet saiti vajadzīgajā ierīcē un piesakieties tajā pašā TOLF kontā. Tiks izvēlēta šī piekļuve. Pēc tam pievienojiet savienojumu un importējiet sertifikātu.", copy:"Kopēt saiti", share:"Kopīgot saiti", copied:"Saite nokopēta", missing:"Šī piekļuve šajā kontā nav pieejama. Piesakieties kontā, kurā tā izveidota."}
  };
  const deliveryCopy = () => DELIVERY_COPY[document.documentElement.lang] || DELIVERY_COPY.en;
  const SESSION_COPY = {
    ru: {connected:"Подключено", disconnected:"Не подключено", checking:"Проверяем подключение…", failed:"Не удалось проверить", forDevice:"для"},
    en: {connected:"Connected", disconnected:"Not connected", checking:"Checking connection…", failed:"Unable to check", forDevice:"for"},
    lv: {connected:"Savienots", disconnected:"Nav savienots", checking:"Pārbauda savienojumu…", failed:"Neizdevās pārbaudīt", forDevice:"ierīcei"}
  };
  const sessionCopy = () => SESSION_COPY[document.documentElement.lang] || SESSION_COPY.en;
  window.updateAnyConnectSessionStatus = () => {
    if (!statusBadge) return;
    const d = devices.find(d => d.id === selectedId);
    if (!d) return;
    const snapshot = window.getAnyConnectSessionStatus?.();
    const state = d.state !== "active" ? d.state : snapshot?.id === d.id ? snapshot.status : "checking";
    const points = state === 'connected' ? Object.entries(snapshot?.nodes || {}).filter(([,value]) => value.connected === true).map(([name]) => ingressCopy()[name]).filter(Boolean) : [];
    statusBadge.textContent = d.state !== "active" ? (d.state === "pending" ? copy().pending : copy().revoking) : sessionCopy()[state] + (points.length ? ' · ' + points.join(', ') : '');
    statusBadge.className = "oc-device-status oc-session-" + state;
  };
  const copy = () => COPY[document.documentElement.lang] || COPY.en;
  const selected = () => devices.find(d => d.id === selectedId && d.state === "active") || null;
  window.ocAccess = { selected, accountUsername: () => account?.vpn?.username || "", ingress, ingresses, selectIngress };
  const path = id => "/oc/access/devices/" + encodeURIComponent(id);
  function connectionUri(d) {
    const point = ingress();
    const prefix = point.id === 'riga' ? 'TOLF Рига ' : 'TOLF Москва ';
    const name = d.connectionNames?.[point.id] || Array.from(prefix + d.label).slice(0,24).join("").trimEnd();
    const params = {name, host:point.host, usecert:"true", certcommonname:d.username, netroam:"true"};
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
    confirmedDeviceId = null;
    importedDeviceId = null;
    transferGrant = null; clearTimeout(transferTimer);
    setupDestination = null; transferNotice = "";
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
    if (!ingresses().some(item => item.id === ingressId)) { ingressId = ingress().id; confirmedDeviceId = null; }
    if (results[1].status === "fulfilled") {
      devices = results[1].value.devices.filter(d => d.state !== "revoked");
      if (!devices.some(d => d.id === selectedId)) {
        selectedId = incomingDevice ? devices.find(d => d.id === incomingDevice)?.id || null : devices.find(d => d.state === "active")?.id || devices[0]?.id || null;
        if (incomingDevice && !selectedId) { message = deliveryCopy().missing; error = true; }
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
    statusBadge = null;
    setupSteps = null;
    root.replaceChildren();
    if (!account) return;
    const c = copy(), mobile = currentPlatform !== "windows";
    const header = element("div", null, "oc-access-header");
    header.append(element("h3", c.title));
    if (devices.length && !addingDevice) header.append(button(c.additional, () => { addingDevice = true; render(); }));
    root.append(header, element("p", c.separate, "oc-note"));
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
      if (!selectedId) { const placeholder = element("option", c.choose); placeholder.value = ""; placeholder.selected = true; select.append(placeholder); }
      for (const d of devices) {
        const opt = element("option", d.label);
        opt.value = d.id; opt.selected = d.id === selectedId; select.append(opt);
      }
      select.addEventListener("change", () => choose(select.value)); row.append(select);
      statusBadge = element("span", null, "oc-device-status");
      statusBadge.setAttribute("role", "status"); statusBadge.setAttribute("aria-live", "polite");
      row.append(statusBadge); window.updateAnyConnectSessionStatus();
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
      const delivery = deliveryCopy();
      const connectionSettings = element('div', null, 'oc-connection-settings');
      if (ingresses().length > 1) {
        const field = element('div', null, 'oc-ingress-field');
        const label = element('label', ingressCopy().label); label.htmlFor = 'ocIngress';
        const select = element('select'); select.id = 'ocIngress'; select.disabled = busy || loading;
        for (const point of ingresses()) { const option = element('option', ingressCopy()[point.id]); option.value = point.id; select.append(option); }
        select.value = ingress().id; select.addEventListener('change', () => selectIngress(select.value));
        field.append(label, select, element('p', ingressCopy().help)); connectionSettings.append(field);
      }
      const destinations = element("div", null, "oc-actions oc-import-actions oc-destinations");
      if (routingControls) connectionSettings.append(routingControls);
      root.append(connectionSettings);
      if (currentPlatform === "ios") {
        // Direct authenticated GET: Safari receives an installable CMS-signed
        // MobileConfig with both the certificate and the Cisco VPN.
        const location = API + path(d.id) + "/ios.mobileconfig?ingress=" + encodeURIComponent(ingress().id);
        const actions = element("div", null, "oc-actions oc-ios-install");
        actions.append(link(c.iosInstall, location, true));
        root.append(actions, element("p", c.iosInstallHelp, "oc-note"));
      }
      for (const [destination, text] of [["local",delivery.local],["remote",delivery.remote]]) {
        if (currentPlatform === "ios" && destination === "local") continue;
        const action = button(text, () => {
          setupDestination = destination; transferNotice = "";
          if (destination === "remote") { grant = null; clearCopyNotice(); clearDownloadedPackage(); }
          render();
          if (destination === "local") {
            setupSteps?.focus?.({preventScroll:true});
            setupSteps?.scrollIntoView?.({behavior:"smooth", block:"start"});
          }
        }, setupDestination === destination);
        action.setAttribute("aria-pressed", String(setupDestination === destination)); destinations.append(action);
      }
      root.append(destinations);
      if (setupDestination === "remote") {
        const transfer = element("section", null, "oc-transfer");
        const t = transferCopy();
        transfer.append(element("h4", delivery.remote + " — «" + d.label + "»"), element("p", t.help, "oc-note"));
        if (transferGrant?.deviceId === d.id && Date.parse(transferGrant.expiresAt) > Date.now()) {
          const setupLink = transferGrant.setupUrl;
          const actions = element("div", null, "oc-actions oc-import-actions oc-transfer-actions");
          const fieldRow = element("div", null, "oc-transfer-field");
          const field = element("input"); field.type = "text"; field.readOnly = true; field.value = setupLink; field.setAttribute("aria-label", delivery.copy); fieldRow.append(field);
          const control = element("span", null, "oc-copy-control");
          const icon = button("", async () => {
            const token = epoch, current = transferGrant;
            try { await copyText(setupLink); if (token !== epoch || transferGrant !== current || selectedId !== d.id) return; transferNotice = delivery.copied; }
            catch { if (token !== epoch || transferGrant !== current) return; transferNotice = c.failed; }
            clearTimeout(transferTimer); render(); transferTimer = setTimeout(() => { transferNotice = ""; render(); }, 2000);
          });
          icon.className = "oc-copy"; icon.setAttribute("aria-label", delivery.copy); icon.title = delivery.copy;
          const glyph = element("span", null, "oc-copy-glyph"); glyph.setAttribute("aria-hidden", "true"); icon.append(glyph); control.append(icon);
          if (transferNotice) { const notice = element("span", transferNotice, "oc-copy-feedback"); notice.setAttribute("role", "status"); control.append(notice); }
          fieldRow.append(control); actions.append(fieldRow);
          actions.append(button(delivery.share, async () => {
            try {
              if (typeof navigator !== "undefined" && navigator.share) await navigator.share({title:"TOLF AnyConnect — " + d.label, url:setupLink});
              else icon.click();
            } catch { }
          }));
          transfer.append(actions, element("p", t.expires + " " + new Date(transferGrant.expiresAt).toLocaleString(), "oc-note"));
        } else {
          const createLink = button(t.create, () => perform(async token => {
            const result = await apiRequest(path(d.id) + "/setup-link", {method:"POST", timeoutMs:30000});
            if (token === epoch && selectedId === d.id) { transferGrant = result; transferNotice = ""; }
          }), true);
          createLink.disabled ||= capabilities?.guestSetup !== true;
          transfer.append(createLink);
          if (capabilities?.guestSetup !== true) transfer.append(element("p", t.update, "oc-note"));
        }
        root.append(transfer);
      } else if (setupDestination === "local" && currentPlatform !== "ios") {
      const steps = element("div", null, "oc-steps");
      setupSteps = steps; steps.setAttribute('tabindex', '-1');
      const suffix = " " + sessionCopy().forDevice + " «" + d.label + "»";
      const connect = element("section", null, "oc-step"); connect.append(element("h4", "3. " + c.connect + suffix + " — " + ingressCopy()[ingress().id]), element("p", c.return));
      if (confirmedDeviceId === d.id) {
        const completed = element("div", null, "oc-connection-completed");
        const status = element("div", completedCopy().done, "oc-connection-done"); status.setAttribute("role", "status");
        const again = button(completedCopy().again, () => { confirmedDeviceId = null; importedDeviceId = null; render(); }); again.className = "oc-action oc-retry-link";
        completed.append(status, again); connect.append(completed);
      } else {
        const actions = element("div", null, "oc-actions oc-connection-actions");
        if (mobile) { connect.append(element("p", c.controlReminder)); actions.append(link(c.add, connectionUri(d), true)); }
        actions.append(button(stepCopy().confirm, () => { confirmedDeviceId = d.id; render(); }));
        connect.append(actions);
      }
      connect.append(element("p", c.host.replace('oc.tolf.is:4443', ingress().host)));
      steps.append(connect);
      const cert = element("section", null, "oc-step"); cert.append(element("h4", "4. " + c.certificate + " — «" + d.label + "»"));
      const prepare = button(c.prepare, () => perform(async token => {
        if (confirmedDeviceId !== d.id) return;
        importedDeviceId = null;
        const id = d.id;
        const result = await apiRequest(path(id) + "/import", { method: "POST", timeoutMs: 30000 });
        if (token === epoch && selectedId === id) { grant = result; clearCopyNotice(); clearDownloadedPackage(); }
      }), true);
      prepare.className += " oc-prepare";
      prepare.disabled ||= capabilities?.issuance !== true || confirmedDeviceId !== d.id;
      if (importedDeviceId === d.id) {
        cert.append(element("p", certificateCopy().done, "oc-certificate-done"), element("p", certificateCopy().help), prepare);
      } else {
        const actions = element("div", null, "oc-actions oc-certificate-actions");
        const already = button(certificateCopy().already, () => {
          if (confirmedDeviceId !== d.id) return;
          importedDeviceId = d.id; grant = null; clearCopyNotice(); clearDownloadedPackage(); render();
        });
        already.disabled ||= confirmedDeviceId !== d.id;
        actions.append(prepare, already);
        cert.append(actions, element("p", confirmedDeviceId === d.id ? certificateCopy().help : stepCopy().blocked, "oc-note"));
      }
      if (grant?.deviceId === d.id && confirmedDeviceId === d.id && importedDeviceId !== d.id) {
        cert.append(element("p", c.password), element("p", c.passwordHelp));
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
      if (importedDeviceId !== d.id) cert.append(element("p", mobile ? c.manual : c.windows, "oc-note")); steps.append(cert);
      const enable = element("section", null, "oc-step");
      enable.append(element("h4", "5. " + c.enableTitle), element("p", c.enable));
      steps.append(enable); root.append(steps);
      }
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
    devices = []; selectedId = null; grant = null; capabilities = null; ingressId = 'moscow';
    setupDestination = incomingDevice ? "local" : null; transferNotice = "";
    confirmedDeviceId = null;
    importedDeviceId = null;
    transferGrant = null; clearTimeout(transferTimer);
    deviceName = ""; creationRequest = null; addingDevice = false; busy = false; loading = false; message = ""; error = false;
    window.refreshAnyConnectTransport?.(); render();
    if (account) refresh();
  };
  for (const event of ["vpntransportchange", "vpnplatformchange"]) window.addEventListener(event, render);
  new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  setInterval(() => {
    if (grant && Date.parse(grant.expiresAt) <= Date.now()) { grant = null; clearCopyNotice(); clearDownloadedPackage(); message = copy().expired; render(); }
  }, 1000);
  window.addEventListener("pagehide", () => { grant = null; confirmedDeviceId = null; importedDeviceId = null; transferGrant = null; transferNotice = ""; clearTimeout(transferTimer); clearCopyNotice(); clearDownloadedPackage(); });
  window.addEventListener("pageshow", render);
  window.setAnyConnectAccount(window.tolfAccountState || null);
  if (incomingDevice) document.getElementById("vpnTransportAnyConnect")?.click();
})();
