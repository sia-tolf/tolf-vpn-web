/* Shared iOS setup controls. Names must match the WebClip URLs and signed files. */
(() => {
  'use strict';
  const TEXT = {
    ru: {
      option: "Установить команды и кнопки VPN",
      help: 'Зелёная TOLF ON включает VPN, красная TOLF OFF выключает. Кнопки установятся вместе с профилем.',
      setup: "Добавьте обе команды, затем установите профиль со значками. TOLF ON настроена на VPN «{vpn}», TOLF OFF отключает активное подключение AnyConnect. Сохраните названия команд.",
      add: 'Добавить ', save: 'Сохранить MobileConfig', saving: 'Сохраняем…',
      failed: 'Не удалось сохранить профиль. Попробуйте ещё раз.',
      note: "После добавления каждой команды в приложении «Команды» вернитесь сюда и подтвердите добавление.",
      confirm: "Команда добавлена — продолжить",
      ready: "3. Установите профиль со значками TOLF ON и TOLF OFF.",
      install: "Установить профиль с кнопками",
    },
    en: {
      option: "Install VPN shortcuts and Home Screen buttons",
      help: 'Green TOLF ON connects VPN; red TOLF OFF disconnects it. The buttons are installed with the profile.',
      setup: "Add both shortcuts, then install the profile with icons. TOLF ON is configured for VPN “{vpn}”; TOLF OFF disconnects the active AnyConnect connection. Keep the shortcut names.",
      add: 'Add ', save: 'Save MobileConfig', saving: 'Saving…',
      failed: 'Unable to save the profile. Please try again.',
      note: "After adding each shortcut in Shortcuts, return here and confirm that it was added.",
      confirm: "Shortcut added — continue",
      ready: "3. Install the profile with TOLF ON and TOLF OFF icons.",
      install: "Install profile with buttons",
    },
    lv: {
      option: "Instalēt VPN komandas un sākuma ekrāna pogas",
      help: 'Zaļā TOLF ON ieslēdz VPN, sarkanā TOLF OFF izslēdz. Pogas tiek instalētas kopā ar profilu.',
      setup: "Pievienojiet abas komandas, pēc tam instalējiet profilu ar ikonām. TOLF ON ir konfigurēta VPN “{vpn}”; TOLF OFF atvieno aktīvo AnyConnect savienojumu. Saglabājiet komandu nosaukumus.",
      add: 'Pievienot ', save: 'Saglabāt MobileConfig', saving: 'Saglabā…',
      failed: 'Neizdevās saglabāt profilu. Mēģiniet vēlreiz.',
      note: "Pēc katras komandas pievienošanas lietotnē Shortcuts atgriezieties šeit un apstipriniet pievienošanu.",
      confirm: "Komanda pievienota — turpināt",
      ready: "3. Instalējiet profilu ar TOLF ON un TOLF OFF ikonām.",
      install: "Instalēt profilu ar pogām",
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
    return state && state.expires > Date.now() && [0, 1, 2].includes(state.step)
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
    else details.append(element('p', ({ru:'Ссылки на команды появятся после подготовки профиля.', en:'Shortcut links appear after the profile is prepared.', lv:'Komandu saites parādīsies pēc profila sagatavošanas.'})[lang] || 'Shortcut links appear after the profile is prepared.'));
    const key = 'tolfIosBundle:' + (url ? profileUrl(url, false) : '') + ':' + (vpnName || '');
    let state = progress(key);
    let save;
    const wizard = element('div', '', 'ios-vpn-wizard');
    details.append(wizard);
    const allowed = () => !checkbox.checked || state.step === 2;
    function renderWizard() {
      wizard.replaceChildren();
      if (save) { save.hidden = !allowed(); save.disabled = disabled || !allowed(); }
      if (!checkbox.checked || !vpnName || !url) return;
      if (state.step < 2) {
        const mode = state.step === 0 ? 'ON' : 'OFF';
        wizard.append(element('p', (state.step + 1) + '. ' + text.add + 'TOLF ' + mode));
        const a = element('a', text.add + 'TOLF ' + mode, 'button-link oc-action secondary');
        const target = new URL(url);
        target.pathname = target.pathname.replace(/\/ios\.mobileconfig$/, '/shortcuts/' + mode.toLowerCase() + '.shortcut');
        target.searchParams.delete('buttons');
        a.href = target.href; a.referrerPolicy = 'no-referrer';
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
          wizard.append(install);
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
