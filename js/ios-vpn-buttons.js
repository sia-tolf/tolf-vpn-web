/* Shared iOS setup controls. Names must match the WebClip URLs and signed files. */
(() => {
  'use strict';
  const TEXT = {
    ru: {
      option: 'Добавить кнопки VPN на главный экран',
      help: 'Зелёная TOLF ON включает VPN, красная TOLF OFF выключает. Кнопки установятся вместе с профилем.',
      setup: '1. Добавьте TOLF ON и TOLF OFF по двум ссылкам ниже. В приложении «Команды» подтвердите добавление каждой команды и вернитесь на эту страницу. TOLF ON уже настроена на VPN «{vpn}», TOLF OFF отключает активное подключение AnyConnect. Сохраните названия команд. При смене точки входа или имени профиля добавьте TOLF ON заново с заменой существующей команды.',
      add: 'Добавить ', save: 'Сохранить MobileConfig', saving: 'Сохраняем…',
      failed: 'Не удалось сохранить профиль. Попробуйте ещё раз.',
      note: 'Команды можно добавить позже. До этого значки не смогут управлять VPN. При запуске приложение «Команды» ненадолго откроется, затем команда вернёт вас на главный экран.'
    },
    en: {
      option: 'Add VPN buttons to the Home Screen',
      help: 'Green TOLF ON connects VPN; red TOLF OFF disconnects it. The buttons are installed with the profile.',
      setup: '1. Add TOLF ON and TOLF OFF using both links below. Confirm each addition in Shortcuts and return to this page. TOLF ON is configured for VPN “{vpn}”; TOLF OFF disconnects the active AnyConnect connection. Keep the shortcut names. After changing the entry point or profile name, add TOLF ON again and replace the existing shortcut.',
      add: 'Add ', save: 'Save MobileConfig', saving: 'Saving…',
      failed: 'Unable to save the profile. Please try again.',
      note: 'You can add the shortcuts later. The icons cannot control VPN until then. Shortcuts briefly opens when launched, then the shortcut returns to the Home Screen.'
    },
    lv: {
      option: 'Pievienot VPN pogas sākuma ekrānam',
      help: 'Zaļā TOLF ON ieslēdz VPN, sarkanā TOLF OFF izslēdz. Pogas tiek instalētas kopā ar profilu.',
      setup: '1. Pievienojiet TOLF ON un TOLF OFF, izmantojot abas saites. Apstipriniet katras komandas pievienošanu lietotnē Shortcuts un atgriezieties šajā lapā. TOLF ON ir konfigurēta VPN “{vpn}”; TOLF OFF atvieno aktīvo AnyConnect savienojumu. Saglabājiet komandu nosaukumus. Mainot ieejas punktu vai profila nosaukumu, pievienojiet TOLF ON vēlreiz, aizstājot esošo komandu.',
      add: 'Pievienot ', save: 'Saglabāt MobileConfig', saving: 'Saglabā…',
      failed: 'Neizdevās saglabāt profilu. Mēģiniet vēlreiz.',
      note: 'Komandas var pievienot vēlāk. Līdz tam ikonas nevar vadīt VPN. Palaižot komandu, īslaicīgi atveras lietotne Shortcuts, pēc tam komanda atgriežas sākuma ekrānā.'
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
    if (vpnName && url) {
      const links = element('div', '', 'oc-actions');
      for (const mode of ['ON', 'OFF']) {
        const a = element('a', text.add + 'TOLF ' + mode, 'button-link oc-action secondary');
        const target = new URL(url);
        target.pathname = target.pathname.replace(/\/ios\.mobileconfig$/, '/shortcuts/' + mode.toLowerCase() + '.shortcut');
        target.searchParams.delete('buttons');
        a.href = target.href;
        a.referrerPolicy = 'no-referrer'; links.append(a);
      }
      details.append(links, element('p', text.note, 'oc-note'));
      details.append(element('p', ({ru:'2. Установите профиль с кнопками. Если профиль уже установлен, повторная установка не нужна.', en:'2. Install the profile with buttons. If it is already installed, you do not need to install it again.', lv:'2. Instalējiet profilu ar pogām. Ja profils jau ir instalēts, atkārtota instalēšana nav nepieciešama.'})[lang] || '2. Install the profile with buttons.'));
      if (includeInstall) {
        const install = element('a', ({ru:'Установить профиль с кнопками',en:'Install profile with buttons',lv:'Instalēt profilu ar pogām'})[lang] || 'Install profile with buttons', 'button-link oc-action');
        install.href = profileUrl(url, true);
        install.referrerPolicy = 'no-referrer';
        details.append(install);
      }
    }
    checkbox.addEventListener('change', () => { details.hidden = !checkbox.checked; onChange(checkbox.checked); });
    root.append(label, details);
    if (url) {
      const save = element('button', text.save, 'oc-action secondary'); save.type = 'button'; save.disabled = disabled;
      const status = element('p', '', 'oc-note'); status.setAttribute('role', 'status');
      save.addEventListener('click', async () => {
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
          save.disabled = disabled; save.textContent = text.save;
        }
      });
      root.append(save, status);
    }
    return root;
  }
  window.tolfIosButtons = {create, profileUrl};
})();
