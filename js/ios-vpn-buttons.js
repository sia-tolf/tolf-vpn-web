/* Shared iOS setup controls. Names must match the WebClip URLs and signed files. */
(() => {
  'use strict';
  // Enable a share only after its published VPN target matches the profile.
  // Historical shares target TOLF Moscow/Riga and cannot control renamed profiles.
  const CITY_SHARES = {
    moscow: '3b5b6270b5464d84866084aad873647b',
    riga: '02ed7a839cee48289255a2a4338392fe',
    us: '823c220015df4b1d92e8fb326f69ebde',
  };
  const CITY_SHORTCUT_NAMES = {
    moscow: 'TOLF Moscow AnyConnect',
    riga: 'TOLF Riga AnyConnect',
    us: 'TOLF New York AnyConnect',
  };
  function shortcutLink(city, vpnName) {
    const id = CITY_SHARES[city];
    return vpnName === CITY_SHORTCUT_NAMES[city] && /^[a-f0-9]{32}$/.test(id || '')
      ? 'https://www.icloud.com/shortcuts/' + id : null;
  }
  const TEXT = {
    ru: {
      permission: 'При первом запуске нажмите «Разрешить» (Allow) для доступа к AnyConnect.',
      option: "Добавить значок управления VPN на экран",
      help: 'Профиль устанавливает значок на экран. Саму команду нужно отдельно добавить в приложение «Команды», иначе значок не сможет управлять VPN.',
      setup: "Настройка состоит из двух шагов: добавьте команду «{shortcut}», затем установите профиль «{vpn}» со значком.",
      add: "Добавить команду «{vpn}»", save: 'Сохранить MobileConfig', saving: 'Сохраняем…',
      failed: 'Не удалось сохранить профиль. Попробуйте ещё раз.',
      note: "Добавьте команду на странице iCloud, затем вернитесь в Safari. Продолжайте только после появления команды в приложении «Команды». Сохраните её название.",
      confirm: "Команда добавлена — продолжить",
      ready: "2. Установите VPN",
      install: "Установить профиль",
      instructions: "После скачивания откройте «Настройки» → «Профиль загружен» → «Установить» и подтвердите установку. На главном экране появится значок TOLF с названием города. Возвращаться на сайт больше не нужно.",
    },
    en: {
      permission: 'On first launch, tap “Allow” to give TOLF access to AnyConnect.',
      option: "Add a VPN control icon to the Home Screen",
      help: 'The profile installs the Home Screen icon. Add its command to Shortcuts separately before using the icon.',
      setup: "Two steps: add the “{shortcut}” shortcut, then install the “{vpn}” VPN profile and icon.",
      add: "Add “{vpn}” shortcut", save: 'Save MobileConfig', saving: 'Saving…',
      failed: 'Unable to save the profile. Please try again.',
      note: "Add the shortcut through iCloud, then return to Safari. Continue only after it appears in Shortcuts. Keep its name.",
      confirm: "Shortcut added — continue",
      ready: "2. Install VPN",
      install: "Install profile",
      instructions: "After downloading, open Settings → Profile Downloaded → Install and confirm. A TOLF icon with the city name will appear on the Home Screen. You do not need to return to this website.",
    },
    lv: {
      permission: 'Pirmajā palaišanas reizē pieskarieties “Atļaut” (Allow), lai TOLF varētu piekļūt AnyConnect.',
      option: "Pievienot VPN vadības ikonu sākuma ekrānam",
      help: 'Profils instalē ikonu sākuma ekrānā. Pati komanda atsevišķi jāpievieno lietotnei Shortcuts, lai ikona varētu vadīt VPN.',
      setup: "Divi soļi: pievienojiet komandu “{shortcut}”, pēc tam instalējiet VPN profilu “{vpn}” ar ikonu.",
      add: "Pievienot komandu “{vpn}”", save: 'Saglabāt MobileConfig', saving: 'Saglabā…',
      failed: 'Neizdevās saglabāt profilu. Mēģiniet vēlreiz.',
      note: "Pievienojiet komandu iCloud lapā, pēc tam atgriezieties Safari. Turpiniet tikai tad, kad komanda redzama lietotnē Shortcuts. Saglabājiet tās nosaukumu.",
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
    const icon = element('span', '⏻', 'ios-vpn-icon ' + (city === 'us' ? 'us' : city === 'riga' ? 'riga' : 'moscow'));
    icon.setAttribute('aria-hidden', 'true');
    item.append(icon, element('strong', vpnName || 'TOLF'));
    preview.append(item);
    details.append(preview, element('p', text.permission, 'oc-note'));
    // Quick Setup supplies the invariant city name after preparation.
    if (vpnName) details.append(element('p', text.setup.replaceAll('{vpn}', vpnName).replace('{shortcut}', vpnName)));
    else details.append(element('p', ({ru:'Сначала добавим команду TOLF, затем установим профиль VPN.', en:'First add the TOLF shortcut, then install the VPN profile.', lv:'Vispirms pievienosim komandu TOLF, pēc tam instalēsim VPN profilu.'})[lang] || 'First add the TOLF shortcut, then install the VPN profile.'));
    const key = 'tolfIosIcloudV5:' + (url ? profileUrl(url, false) : '') + ':' + (vpnName || '');
    let state = progress(key);
    let save;
    const wizard = element('div', '', 'ios-vpn-wizard');
    details.append(wizard);
    const allowed = () => !checkbox.checked || (state.step === 1 && !!shortcutLink(city, vpnName));
    function renderWizard() {
      wizard.replaceChildren();
      if (save) { save.hidden = !allowed(); save.disabled = disabled || !allowed(); }
      if (!checkbox.checked || !vpnName || !url) return;
      {
        const addLabel = text.add.replace('{vpn}', vpnName);
        const link = shortcutLink(city, vpnName);
        if (!link) {
          wizard.append(element('p', ({ru:'Добавление значка временно недоступно: обновлённая команда iCloud ещё не опубликована. Профиль можно установить без значка.', en:'The icon is temporarily unavailable: the updated iCloud shortcut has not been published. You can install the profile without the icon.', lv:'Ikona īslaicīgi nav pieejama: atjauninātā iCloud komanda vēl nav publicēta. Profilu var instalēt bez ikonas.'})[lang] || 'The shortcut is not available yet.', 'oc-note'));
          return;
        }
        wizard.append(element('p', '1. ' + addLabel));
        const a = element('a', addLabel, 'button-link oc-action secondary');
        a.href = link;
        a.referrerPolicy = 'no-referrer';
        a.textContent = addLabel;
        const confirm = element('button', text.confirm, 'oc-action');
        confirm.hidden = state.step === 1;
        confirm.type = 'button'; confirm.disabled = disabled || !state.opened;
        a.addEventListener('click', event => {
          if (disabled) { event?.preventDefault(); return; }
          state.opened = true; progress(key, state); confirm.disabled = false;
        });
        confirm.addEventListener('click', () => {
          if (disabled || !state.opened || state.step === 1) return;
          state = progress(key, {...state, step:state.step + 1, opened:false});
          renderWizard();
        });
        wizard.append(a, element('p', text.note, 'oc-note'), confirm);
      }
      if (state.step === 1) {
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
