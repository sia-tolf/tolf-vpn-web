/* Shared iOS setup controls. Names must match the WebClip URLs and signed files. */
(() => {
  'use strict';
  // Populate with verified iCloud shares before deploying this release.
  const CITY_SHARES = {
    moscow: null,
    riga: null,
  };
  function shortcutLink(city) {
    const id = CITY_SHARES[city];
    return /^[a-f0-9]{32}$/.test(id || '') ? 'https://www.icloud.com/shortcuts/' + id : null;
  }
  const TEXT = {
    ru: {
      permission: 'При первом запуске нажмите «Разрешить» (Allow) для доступа к AnyConnect.',
      option: "Добавить значок управления VPN на экран",
      help: 'Один значок для этого подключения. Он открывает меню включения и выключения VPN с названием города.',
      setup: "Настройка состоит из двух шагов: добавьте команду «{vpn}», затем установите профиль «{vpn}» со значком.",
      add: "Добавить команду «{vpn}»", save: 'Сохранить MobileConfig', saving: 'Сохраняем…',
      failed: 'Не удалось сохранить профиль. Попробуйте ещё раз.',
      note: "Подтвердите добавление в приложении «Команды», затем вернитесь на эту страницу в Safari. Заменяйте только одноимённую команду. Сохраните её название.",
      confirm: "Команда добавлена — продолжить",
      ready: "2. Установите VPN",
      install: "Установить профиль",
      instructions: "После скачивания откройте «Настройки» → «Профиль загружен» → «Установить» и подтвердите установку. На главном экране появится значок TOLF с названием города. Возвращаться на сайт больше не нужно.",
    },
    en: {
      permission: 'On first launch, tap “Allow” to give TOLF access to AnyConnect.',
      option: "Add a VPN control icon to the Home Screen",
      help: 'One icon for this connection opens a VPN on/off menu showing the city.',
      setup: "Two steps: add the “{vpn}” shortcut, then install the “{vpn}” VPN profile and icon.",
      add: "Add “{vpn}” shortcut", save: 'Save MobileConfig', saving: 'Saving…',
      failed: 'Unable to save the profile. Please try again.',
      note: "Confirm the addition in Shortcuts, then return to this page in Safari. Replace only the shortcut with the same name. Keep its name.",
      confirm: "Shortcut added — continue",
      ready: "2. Install VPN",
      install: "Install profile",
      instructions: "After downloading, open Settings → Profile Downloaded → Install and confirm. A TOLF icon with the city name will appear on the Home Screen. You do not need to return to this website.",
    },
    lv: {
      permission: 'Pirmajā palaišanas reizē pieskarieties “Atļaut” (Allow), lai TOLF varētu piekļūt AnyConnect.',
      option: "Pievienot VPN vadības ikonu sākuma ekrānam",
      help: 'Viena ikona šim savienojumam atver VPN ieslēgšanas un izslēgšanas izvēlni ar pilsētas nosaukumu.',
      setup: "Divi soļi: pievienojiet komandu “{vpn}”, pēc tam instalējiet VPN profilu “{vpn}” ar ikonu.",
      add: "Pievienot komandu “{vpn}”", save: 'Saglabāt MobileConfig', saving: 'Saglabā…',
      failed: 'Neizdevās saglabāt profilu. Mēģiniet vēlreiz.',
      note: "Apstipriniet pievienošanu lietotnē Shortcuts, pēc tam atgriezieties šajā lapā pārlūkā Safari. Aizstājiet tikai komandu ar tādu pašu nosaukumu. Saglabājiet tās nosaukumu.",
      confirm: "Komanda pievienota — turpināt",
      ready: "2. Instalējiet VPN",
      install: "Instalēt profilu",
      instructions: "Pēc lejupielādes atveriet Iestatījumi → Lejupielādēts profils → Instalēt un apstipriniet. Sākuma ekrānā parādīsies TOLF ikona ar pilsētas nosaukumu. Šajā vietnē vairs nav jāatgriežas.",
    }
  };
  function element(tag, text, cls) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }
  function profileUrl(url, checked) {
    const result = new URL(url);
    if (checked) result.searchParams.set('buttons', 'true');
    else result.searchParams.delete('buttons');
    return result.href;
  }
  const memory = new Map();
  function progress(key, value) {
    if (value) {
      memory.set(key, value);
      try { sessionStorage.setItem(key, JSON.stringify(value)); } catch {}
      return value;
    }
    let state = memory.get(key);
    try { state = state || JSON.parse(sessionStorage.getItem(key)); } catch {}
    return state && state.expires > Date.now() && [0, 1].includes(state.step)
      ? state : {step:0, opened:false, expires:Date.now() + 2 * 60 * 60 * 1000};
  }
  function create({checked = false, onChange, vpnName, url, includeInstall = false, saveHost = null, disabled = false, lang = document.documentElement.lang}) {
    const text = TEXT[lang] || TEXT.en;
    const root = element('section', '', 'ios-vpn-buttons');
    const label = element('label', '', 'ios-vpn-buttons-choice');
    const checkbox = element('input'); checkbox.type = 'checkbox';
    checkbox.checked = checked; checkbox.disabled = disabled;
    label.append(checkbox, element('span', text.option));
    const details = element('div', '', 'ios-vpn-buttons-details'); details.hidden = !checked;
    details.append(element('p', text.help));
    const preview = element('div', '', 'ios-vpn-buttons-preview');
    const item = element('div');
    const city = url ? new URL(url).searchParams.get('ingress') : '';
    const icon = element('span', '⏻', 'ios-vpn-icon ' + (city === 'riga' ? 'riga' : 'moscow'));
    icon.setAttribute('aria-hidden', 'true');
    item.append(icon, element('strong', vpnName ? vpnName.split(' ').slice(0,2).join(' ') : 'TOLF'));
    preview.append(item);
    details.append(preview, element('p', text.permission, 'oc-note'));
    // Quick Setup supplies the invariant city name after preparation.
    if (vpnName) details.append(element('p', text.setup.replaceAll('{vpn}', vpnName)));
    else details.append(element('p', ({ru:'Сначала добавим команду TOLF, затем установим профиль VPN.', en:'First add the TOLF shortcut, then install the VPN profile.', lv:'Vispirms pievienosim komandu TOLF, pēc tam instalēsim VPN profilu.'})[lang] || 'First add the TOLF shortcut, then install the VPN profile.'));
    const key = 'tolfIosCityV2:' + (url ? profileUrl(url, false) : '') + ':' + (vpnName || '');
    let state = progress(key);
    let save;
    const wizard = element('div', '', 'ios-vpn-wizard');
    details.append(wizard);
    const allowed = () => !checkbox.checked || state.step === 1;
    function renderWizard() {
      wizard.replaceChildren();
      if (save) { save.hidden = !allowed(); save.disabled = disabled || !allowed(); }
      if (!checkbox.checked || !vpnName || !url) return;
      if (state.step < 1) {
        const addLabel = text.add.replace('{vpn}', vpnName);
        const link = shortcutLink(city);
        if (!link) {
          wizard.append(element('p', ({ru:'Команда пока недоступна.', en:'The shortcut is not available yet.', lv:'Komanda vēl nav pieejama.'})[lang] || 'The shortcut is not available yet.', 'oc-note'));
          return;
        }
        wizard.append(element('p', '1. ' + addLabel));
        const a = element('a', addLabel, 'button-link oc-action secondary');
        a.href = link;
        a.referrerPolicy = 'no-referrer';
        a.textContent = addLabel;
        const confirm = element('button', text.confirm, 'oc-action');
        confirm.type = 'button'; confirm.disabled = disabled || !state.opened;
        a.addEventListener('click', event => {
          if (disabled) { event?.preventDefault(); return; }
          state.opened = true; progress(key, state); confirm.disabled = false;
        });
        confirm.addEventListener('click', () => {
          if (disabled || !state.opened) return;
          state = progress(key, {...state, step:state.step + 1, opened:false});
          renderWizard();
        });
        wizard.append(a, element('p', text.note, 'oc-note'), confirm);
      } else {
        wizard.append(element('p', text.ready));
        if (includeInstall) {
          const install = element('a', text.install, 'button-link oc-action primary');
          install.href = profileUrl(url, true); install.referrerPolicy = 'no-referrer';
          install.addEventListener('click', event => { if (disabled || !allowed()) event?.preventDefault(); });
          wizard.append(install, element('p', text.instructions, 'oc-note'));
        }
      }
    }
    checkbox.addEventListener('change', () => {
      details.hidden = !checkbox.checked;
      if (!checkbox.checked) state = progress(key, {step:0, opened:false, expires:Date.now() + 2 * 60 * 60 * 1000});
      renderWizard();
      onChange?.(checkbox.checked);
    });
    root.append(label, details);
    if (url) {
      save = element('button', text.save, 'oc-action secondary'); save.type = 'button'; save.disabled = disabled;
      const status = element('p', '', 'oc-note'); status.setAttribute('role', 'status');
      save.addEventListener('click', async () => {
        if (disabled || !allowed() || save.disabled) return;
        save.disabled = true; save.textContent = text.saving; status.textContent = '';
        let objectUrl;
        try {
          const response = await fetch(profileUrl(url, checkbox.checked), {credentials:'include', cache:'no-store'});
          if (!response.ok) throw Error('Profile download failed');
          const bytes = await response.arrayBuffer();
          objectUrl = URL.createObjectURL(new Blob([bytes], {type:'application/octet-stream'}));
          const a = element('a'); a.href = objectUrl; a.download = 'TOLF-AnyConnect.mobileconfig';
          document.body.append(a); a.click(); a.remove();
        } catch { status.textContent = text.failed; }
        finally {
          if (objectUrl) setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
          save.disabled = disabled || !allowed(); save.textContent = text.save;
        }
      });
      (saveHost || root).append(save);
      root.append(status);
    }
    renderWizard();
    return root;
  }
  window.tolfIosButtons = {create, profileUrl};
})();
