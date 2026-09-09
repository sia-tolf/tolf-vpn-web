function profileSettingsChanged() {
  setInstallLink(null);
  vpnMessage.textContent = "";
  vpnMessage.className = "message";
}

function splitDnsServers(value) {
  return value
    .split(/[\s,;]+/)
    .map(server => server.trim())
    .filter(Boolean);
}

function isIpv4Address(value) {
  const parts = value.split(".");

  return parts.length === 4 && parts.every(part => {
    if (!/^\d{1,3}$/.test(part)) return false;
    if (part.length > 1 && part.startsWith("0")) return false;

    const number = Number(part);
    return number >= 0 && number <= 255;
  });
}

function isIpv6Address(value) {
  if (!value.includes(":")) return false;
  if (!/^[0-9a-f:]+$/i.test(value)) return false;
  if ((value.match(/::/g) || []).length > 1) return false;

  const halves = value.split("::");
  const left = halves[0] ? halves[0].split(":") : [];
  const right = halves[1] ? halves[1].split(":") : [];
  const groups = [...left, ...right];

  if (!groups.every(group => /^[0-9a-f]{1,4}$/i.test(group))) {
    return false;
  }

  return halves.length === 2
    ? groups.length < 8
    : groups.length === 8;
}

function isDnsServerAddress(value) {
  return isIpv4Address(value) || isIpv6Address(value);
}

function validateDnsSettings({ focus = false } = {}) {
  if (!dnsMode || !dnsServersInput || !dnsValidation) {
    return [];
  }

  if (dnsMode.value !== "custom") {
    dnsValidation.textContent = "";
    dnsServersInput.removeAttribute("aria-invalid");
    return [];
  }

  const servers = splitDnsServers(dnsServersInput.value);
  const valid =
    servers.length > 0 &&
    servers.every(isDnsServerAddress);

  dnsValidation.textContent = valid
    ? t("dnsCustomReady", { count: servers.length })
    : t("dnsInvalid");

  dnsValidation.className = valid
    ? "settings-validation"
    : "settings-validation error";

  dnsServersInput.setAttribute("aria-invalid", String(!valid));

  if (!valid && focus) {
    profileSettings.open = true;
    dnsServersInput.focus();
  }

  return valid ? servers : null;
}

function updateDnsVisibility() {
  if (!dnsMode || !dnsCustomGroup) return;

  const custom = dnsMode.value === "custom";
  dnsCustomGroup.classList.toggle("hidden", !custom);

  if (!custom && dnsValidation) {
    dnsValidation.textContent = "";
  }
}

function updateOnDemandVisibility() {
  if (!onDemandEnabled || !onDemandOptions) return;

  const enabled = onDemandEnabled.checked;
  const useAlwaysOn = enabled && alwaysOn.checked;

  onDemandOptions.classList.toggle("hidden", !enabled);
  alwaysOnHint.classList.toggle("hidden", !useAlwaysOn);
  manualOnDemandRules.classList.toggle(
    "hidden",
    !enabled || useAlwaysOn
  );
}

function createOnDemandRule(initialValue = "", initialAction = "Disconnect") {
  if (!onDemandRules || !addOnDemandRule) return null;

  const row = document.createElement("div");
  row.className = "on-demand-rule";

  const network = document.createElement("input");
  network.type = "text";
  network.className = "settings-input on-demand-network";
  network.value = initialValue;
  network.maxLength = 32;
  network.autocomplete = "off";
  network.spellcheck = false;
  network.dataset.i18nPlaceholder = "wifiNetworkName";
  network.placeholder = t("wifiNetworkName");
  network.setAttribute("aria-label", t("wifiNetworkName"));

  const action = document.createElement("select");
  action.className = "settings-select on-demand-rule-action";
  action.setAttribute("aria-label", t("onDemandAction"));

  for (const value of ON_DEMAND_ACTIONS) {
    const option = document.createElement("option");
    option.value = value;
    option.dataset.i18n = `onDemand${value}`;
    option.textContent = t(option.dataset.i18n);
    action.appendChild(option);
  }

  action.value = ON_DEMAND_ACTIONS.includes(initialAction)
    ? initialAction
    : "Disconnect";

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "remove-on-demand-rule";
  remove.textContent = "×";
  remove.setAttribute("aria-label", t("removeOnDemandRule"));

  network.addEventListener("input", profileSettingsChanged);
  action.addEventListener("change", profileSettingsChanged);
  remove.addEventListener("click", () => {
    row.remove();
    profileSettingsChanged();
  });

  row.append(network, action, remove);
  onDemandRules.insertBefore(row, addOnDemandRule);
  return row;
}

function readOnDemandRules({ focus = false } = {}) {
  if (currentPlatform !== "ios" || !onDemandEnabled?.checked) {
    return {
      enabled: false,
      alwaysOn: false,
      rules: []
    };
  }

  if (alwaysOn.checked) {
    return {
      enabled: true,
      alwaysOn: true,
      rules: [{ Action: "Connect" }]
    };
  }

  const rules = [];

  for (const row of onDemandRules.querySelectorAll(".on-demand-rule")) {
    const network = row.querySelector(".on-demand-network");
    const action = row.querySelector(".on-demand-rule-action");
    const value = network.value.trim();

    if (!value) {
      network.setAttribute("aria-invalid", "true");

      if (focus) {
        profileSettings.open = true;
        network.focus();
      }

      return null;
    }

    network.removeAttribute("aria-invalid");
    rules.push({
      Action: action.value,
      InterfaceTypeMatch: "WiFi",
      SSIDMatch: [value]
    });
  }

  rules.push(
    { Action: wifiAction.value, InterfaceTypeMatch: "WiFi" },
    { Action: cellularAction.value, InterfaceTypeMatch: "Cellular" },
    { Action: ethernetAction.value, InterfaceTypeMatch: "Ethernet" },
    { Action: "Ignore" }
  );

  return {
    enabled: true,
    alwaysOn: false,
    rules
  };
}

function getProfileSettingsSelection() {
  const servers = validateDnsSettings({ focus: true });

  if (servers === null) return null;

  const onDemand = readOnDemandRules({ focus: true });

  if (!onDemand) return null;

  return {
    dns: {
      mode: dnsMode?.value === "custom" ? "custom" : "automatic",
      servers
    },
    onDemand
  };
}

function setProfileSettingsBusy(value) {
  profileSettings
    ?.querySelectorAll("input, select, button")
    .forEach(control => {
      control.disabled = value;
    });
}

function renderProfileSettings() {
  updateDnsVisibility();
  updateOnDemandVisibility();

  document
    .querySelectorAll("[data-i18n-placeholder]")
    .forEach(input => {
      input.placeholder = t(input.dataset.i18nPlaceholder);
    });

  document
    .querySelectorAll(".on-demand-network")
    .forEach(input => input.setAttribute("aria-label", t("wifiNetworkName")));

  document
    .querySelectorAll(".on-demand-rule-action")
    .forEach(select => select.setAttribute("aria-label", t("onDemandAction")));

  document
    .querySelectorAll(".remove-on-demand-rule")
    .forEach(button => button.setAttribute("aria-label", t("removeOnDemandRule")));

  if (dnsMode?.value === "custom" && dnsServersInput?.value.trim()) {
    validateDnsSettings();
  }
}

function resetProfileSettings() {
  if (dnsMode) dnsMode.value = "automatic";
  if (dnsServersInput) dnsServersInput.value = "";
  if (onDemandEnabled) onDemandEnabled.checked = false;
  if (alwaysOn) alwaysOn.checked = false;
  if (wifiAction) wifiAction.value = "Connect";
  if (cellularAction) cellularAction.value = "Connect";
  if (ethernetAction) ethernetAction.value = "Connect";

  onDemandRules
    ?.querySelectorAll(".on-demand-rule")
    .forEach(rule => rule.remove());

  renderProfileSettings();
}

dnsMode?.addEventListener("change", () => {
  updateDnsVisibility();
  validateDnsSettings();
  profileSettingsChanged();
});

dnsServersInput?.addEventListener("input", () => {
  validateDnsSettings();
  profileSettingsChanged();
});

onDemandEnabled?.addEventListener("change", () => {
  updateOnDemandVisibility();
  profileSettingsChanged();
});

alwaysOn?.addEventListener("change", () => {
  updateOnDemandVisibility();
  profileSettingsChanged();
});

for (const select of [wifiAction, cellularAction, ethernetAction]) {
  select?.addEventListener("change", profileSettingsChanged);
}

addOnDemandRule?.addEventListener("click", () => {
  const row = createOnDemandRule();
  row?.querySelector(".on-demand-network")?.focus();
  profileSettingsChanged();
});

renderProfileSettings();
