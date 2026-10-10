/* Shared iOS setup controls. Names must match the WebClip URLs and signed files. */
(() => {
  'use strict';
  const TEXT = {
    ru: {
      option: "Установить управление VPN и кнопки на экран",
      help: 'Зелёная TOLF ON включает VPN, красная TOLF OFF выключает. Кнопки установятся вместе с профилем.',
      setup: "Настройка состоит из двух шагов: добавьте одну команду TOLF, затем установите VPN «{vpn}» со значками.",
      add: "Добавить команду TOLF", save: 'Сохранить MobileConfig', saving: 'Сохраняем…',
      failed: 'Не удалось сохранить профиль. Попробуйте ещё раз.',
      note: "Подтвердите добавление в приложении «Команды», затем вернитесь на эту страницу в Safari. Если TOLF уже есть, выберите замену. Сохраните название TOLF.",
      confirm: "Команда добавлена — продолжить",
      ready: "2. Установите VPN",
      install: "Скачать профиль VPN",
      instructions: "После скачивания откройте «Настройки» → «Профиль загружен» → «Установить» и подтвердите установку. На главном экране появятся TOLF ON и TOLF OFF. Возвращаться на сайт больше не нужно.",
    },
    en: {
      option: "Install VPN controls and Home Screen buttons",
      help: 'Green TOLF ON connects VPN; red TOLF OFF disconnects it. The buttons are installed with the profile.',
      setup: "Two steps: add one TOLF shortcut, then install VPN “{vpn}” with its icons.",
      add: "Add TOLF shortcut", save: 'Save MobileConfig', saving: 'Saving…',
      failed: 'Unable to save the profile. Please try again.',
      note: "Confirm the addition in Shortcuts, then return to this page in Safari. If TOLF already exists, replace it. Keep the name TOLF.",
      confirm: "Shortcut added — continue",
      ready: "2. Install VPN",
      install: "Download VPN profile",
      instructions: "After downloading, open Settings → Profile Downloaded → Install and confirm. TOLF ON and TOLF OFF will appear on the Home Screen. You do not need to return to this website.",
    },
    lv: {
      option: "Instalēt VPN vadību un sākuma ekrāna pogas",
      help: 'Zaļā TOLF ON ieslēdz VPN, sarkanā TOLF OFF izslēdz. Pogas tiek instalētas kopā ar profilu.',
      setup: "Divi soļi: pievienojiet vienu komandu TOLF, pēc tam instalējiet VPN “{vpn}” ar ikonām.",
      add: "Pievienot komandu TOLF", save: 'Saglabāt MobileConfig', saving: 'Saglabā…',
      failed: 'Neizdevās saglabāt profilu. Mēģiniet vēlreiz.',
      note: "Apstipriniet pievienošanu lietotnē Shortcuts, pēc tam atgriezieties šajā lapā pārlūkā Safari. Ja TOLF jau ir pievienota, aizstājiet to. Saglabājiet nosaukumu TOLF.",
      confirm: "Komanda pievienota — turpināt",
      ready: "2. Instalējiet VPN",
      install: "Lejupielādēt VPN profilu",
      instructions: "Pēc lejupielādes atveriet Iestatījumi → Lejupielādēts profils → Instalēt un apstipriniet. Sākuma ekrānā parādīsies TOLF ON un TOLF OFF. Šajā vietnē vairs nav jāatgriežas.",
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
  function create({checked = false, onChange, vpnName, url, includeInstall = false, disabled = false, lang = document.documentElement.lang}) {
    const text = TEXT[lang] || TEXT.en;
    const root = element('section', '', 'ios-vpn-buttons');
    const label = element('label', '', 'ios-vpn-buttons-choice');
    const checkbox = element('input'); checkbox.type = 'checkbox';
    checkbox.checked = checked; checkbox.disabled = disabled;
    label.append(checkbox, element('span', text.option));
    const details = element('div', '', 'ios-vpn-buttons-details'); details.hidden = !checked;
    details.append(element('p', text.help));
    const preview = element('div', '', 'ios-vpn-buttons-preview');
    for (const mode of ['on', 'off']) {
      const item = element('div');
      const icon = element('span', mode === 'on' ? '⏻' : '■', 'ios-vpn-icon ' + mode);
      icon.setAttribute('aria-hidden', 'true');
      item.append(icon, element('strong', 'TOLF ' + mode.toUpperCase())); preview.append(item);
    }
    details.append(preview);
    // Quick Setup knows the final device label only after preparation.
    if (vpnName) details.append(element('p', text.setup.replace('{vpn}', vpnName)));
    else details.append(element('p', ({ru:'Сначала добавим команду TOLF, затем установим профиль VPN.', en:'First add the TOLF shortcut, then install the VPN profile.', lv:'Vispirms pievienosim komandu TOLF, pēc tam instalēsim VPN profilu.'})[lang] || 'First add the TOLF shortcut, then install the VPN profile.'));
    const key = 'tolfIosControllerV3:' + (url ? profileUrl(url, false) : '') + ':' + (vpnName || '');
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
        wizard.append(element('p', '1. ' + text.add));
        const a = element('a', text.add, 'button-link oc-action secondary');
        const target = new URL(url);
        target.pathname = target.pathname.replace(/\/ios\.mobileconfig$/, '/shortcuts/control.shortcut');
        target.searchParams.delete('buttons');
        // Verified On Demand controller; its connection name must match exactly.
        const shared = vpnName === 'TOLF Москва iPhone';
        a.href = shared ? 'https://www.icloud.com/shortcuts/ac8daef5b6a94a4c9ac2daeaaa559945' : target.href;
        a.referrerPolicy = 'no-referrer';
        if (!shared) {
        a.textContent = ({ru:'Скачать команду TOLF',en:'Download TOLF shortcut',lv:'Lejupielādēt komandu TOLF'})[lang] || 'Download TOLF shortcut';
        wizard.append(element('p', ({ru:'Откройте скачанный файл TOLF.shortcut из загрузок Safari и добавьте его в «Команды». Если TOLF уже установлена, замените её.',en:'Open TOLF.shortcut from Safari Downloads and add it to Shortcuts. Replace TOLF if already installed.',lv:'Atveriet TOLF.shortcut failu Safari lejupielādēs un pievienojiet to lietotnei Shortcuts. Ja TOLF jau ir instalēta, aizstājiet to.'})[lang] || 'Open TOLF.shortcut from Safari Downloads and add it to Shortcuts.', 'oc-note'));
        }
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
          const install = element('a', text.install, 'button-link oc-action');
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
      root.append(save, status);
    }
    renderWizard();
    return root;
  }
  window.tolfIosButtons = {create, profileUrl};
})();
