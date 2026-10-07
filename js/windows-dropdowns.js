// Same expanding menu as the protocol and entry point fields.
(() => {
  if (!window.makeVpnDropdown) return;
  const dropdowns = [];
  for (const id of ['windowsDeviceServer', 'windowsDeviceMode']) {
    const select = document.getElementById(id);
    const label = document.querySelector('label[for="' + id + '"]');
    if (!select || !label) continue;
    label.id = id + 'Label';
    const dropdown = window.makeVpnDropdown(id + 'Dropdown', '', [], value => {
      select.value = value;
      select.dispatchEvent(new Event('change', {bubbles: true}));
      sync();
    });
    dropdown.label.hidden = true;
    dropdown.field.classList.add('windows-dropdown-field');
    const button = dropdown.field.querySelector('.vpn-dropdown-button');
    button.setAttribute('aria-labelledby', label.id + ' ' + id + 'Value');
    dropdown.field.querySelector('.vpn-dropdown-value').id = id + 'Value';
    if (select.getAttribute('aria-describedby')) button.setAttribute('aria-describedby', select.getAttribute('aria-describedby'));
    select.hidden = true;
    select.insertAdjacentElement('afterend', dropdown.field);
    label.htmlFor = '';
    label.addEventListener('click', () => button.focus());
    select.addEventListener('change', sync);
    new MutationObserver(sync).observe(select, {subtree: true, childList: true, characterData: true, attributes: true});
    dropdowns.push({select, dropdown, button});
    button.addEventListener('keydown', event => {
      if (['ArrowDown','ArrowUp'].includes(event.key)) {
        event.preventDefault();
        if (button.getAttribute('aria-expanded') !== 'true') button.click();
        const options = [...dropdown.field.querySelectorAll('.vpn-dropdown-option:not(:disabled)')];
        (event.key === 'ArrowDown' ? options[0] : options.at(-1))?.focus();
      }
    });
    dropdown.field.addEventListener('keydown', event => {
      const options = [...dropdown.field.querySelectorAll('.vpn-dropdown-option:not(:disabled)')];
      const index = options.indexOf(document.activeElement);
      if (index >= 0 && ['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        event.preventDefault();
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length;
        options[next]?.focus();
      }
      if (event.key === 'Escape') { dropdown.close(); button.focus(); }
      if (event.key === 'Tab') dropdown.close();
    });
  }
  function sync() {
    for (const {select, dropdown, button} of dropdowns) {
      button.disabled = select.disabled;
      if (button.disabled) dropdown.close();
      dropdown.render([...select.options].map(option => ({value: option.value, label: option.textContent, disabled: option.disabled})), select.value);
    }
  }
  window.syncWindowsDropdowns = sync;
  sync();
})();
