const ROUTING_RULE_EXITS = [
  { key: "riga", nameKey: "routingExitRiga", flag: "🇱🇻", available: true },
  { key: "moscow", nameKey: "routingExitMoscow", flag: "🇷🇺", available: true },
  { key: "usa", nameKey: "routingExitUsa", flag: "🇺🇸", available: false }
];

let routingRulesByExit = {
  riga: [],
  moscow: [],
  usa: []
};

function routingRulesChanged() {
  if (typeof profileSettingsChanged === "function") {
    profileSettingsChanged();
  }
}

function normalizeRoutingDomain(rawValue) {
  let value = String(rawValue || "").trim().toLowerCase();
  if (!value) return null;

  value = value.replace(/^\*\./, "");

  try {
    const parsed = new URL(
      value.includes("://") ? value : `https://${value}`
    );

    if (parsed.username || parsed.password || parsed.port) return null;
    value = parsed.hostname.replace(/\.$/, "").toLowerCase();
  } catch {
    return null;
  }

  if (
    value.length > 253 ||
    !value.includes(".") ||
    value.includes(":") ||
    /^\d+(?:\.\d+){3}$/.test(value)
  ) {
    return null;
  }

  const labels = value.split(".");
  const valid = labels.every(label => (
    label.length > 0 &&
    label.length <= 63 &&
    /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(label)
  ));

  return valid ? value : null;
}

function findRoutingDomain(domain) {
  for (const exit of ROUTING_RULE_EXITS) {
    if (routingRulesByExit[exit.key].includes(domain)) {
      return exit;
    }
  }

  return null;
}

function showRoutingRulesMessage(key = "", replacements = {}, error = false) {
  if (!routingRulesValidation) return;

  routingRulesValidation.textContent = key ? t(key, replacements) : "";
  routingRulesValidation.className = error
    ? "settings-validation error"
    : "settings-validation";
}

function closeRoutingRuleEditors() {
  routingRuleGroups
    ?.querySelectorAll(".routing-rule-editor")
    .forEach(editor => editor.remove());

  routingRuleGroups
    ?.querySelectorAll(".routing-rule-add")
    .forEach(button => button.classList.remove("hidden"));
}

function addRoutingDomain(exitKey, input) {
  const domain = normalizeRoutingDomain(input.value);

  if (!domain) {
    input.setAttribute("aria-invalid", "true");
    showRoutingRulesMessage("routingDomainInvalid", {}, true);
    input.focus();
    return false;
  }

  const existingExit = findRoutingDomain(domain);
  if (existingExit) {
    input.setAttribute("aria-invalid", "true");
    showRoutingRulesMessage(
      "routingDomainDuplicate",
      { server: t(existingExit.nameKey) },
      true
    );
    input.focus();
    return false;
  }

  routingRulesByExit[exitKey].push(domain);
  routingRulesByExit[exitKey].sort((left, right) => left.localeCompare(right));
  showRoutingRulesMessage("routingDomainAdded", { domain });
  routingRulesChanged();
  renderRoutingRules();
  return true;
}

function openRoutingRuleEditor(exitKey, group, addButton) {
  closeRoutingRuleEditors();
  addButton.classList.add("hidden");

  const editor = document.createElement("div");
  editor.className = "routing-rule-editor";

  const input = document.createElement("input");
  input.type = "text";
  input.className = "settings-input";
  input.maxLength = 253;
  input.autocomplete = "off";
  input.autocapitalize = "none";
  input.spellcheck = false;
  input.placeholder = t("routingDomainPlaceholder");
  input.setAttribute("aria-label", t("routingDomainLabel"));

  const save = document.createElement("button");
  save.type = "button";
  save.className = "routing-rule-save";
  save.textContent = t("routingSave");

  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "routing-rule-cancel";
  cancel.textContent = t("routingCancel");

  const submit = () => addRoutingDomain(exitKey, input);
  const dismiss = () => {
    editor.remove();
    addButton.classList.remove("hidden");
    showRoutingRulesMessage();
  };

  input.addEventListener("input", () => {
    input.removeAttribute("aria-invalid");
    showRoutingRulesMessage();
  });
  input.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      submit();
    } else if (event.key === "Escape") {
      event.preventDefault();
      dismiss();
    }
  });
  save.addEventListener("click", submit);
  cancel.addEventListener("click", dismiss);

  editor.append(input, save, cancel);
  group.appendChild(editor);
  input.focus();
}

function createRoutingRuleGroup(exit) {
  const group = document.createElement("section");
  group.className = "routing-rule-group";
  group.dataset.exit = exit.key;
  group.dataset.available = String(exit.available);

  const header = document.createElement("div");
  header.className = "routing-rule-group-header";

  const title = document.createElement("div");
  title.className = "routing-rule-group-title";

  const flag = document.createElement("span");
  flag.setAttribute("aria-hidden", "true");
  flag.textContent = exit.flag;

  const name = document.createElement("span");
  name.textContent = t(exit.nameKey);

  const count = document.createElement("span");
  count.className = "routing-rule-count";
  count.textContent = String(routingRulesByExit[exit.key].length);
  count.setAttribute(
    "aria-label",
    t("routingSitesCount", { count: routingRulesByExit[exit.key].length })
  );

  title.append(flag, name);
  header.append(title, count);

  if (!exit.available) {
    count.className = "routing-rule-status";
    count.textContent = t("comingSoon");
  }

  const list = document.createElement("div");
  list.className = "routing-rule-list";
  list.dataset.emptyLabel = t("routingNoSites");

  for (const domain of routingRulesByExit[exit.key]) {
    const item = document.createElement("div");
    item.className = "routing-rule-item";

    const domainText = document.createElement("span");
    domainText.className = "routing-rule-domain";
    domainText.textContent = domain;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "routing-rule-remove";
    remove.textContent = "×";
    remove.setAttribute(
      "aria-label",
      t("routingRemoveDomain", { domain })
    );
    remove.addEventListener("click", () => {
      routingRulesByExit[exit.key] = routingRulesByExit[exit.key]
        .filter(value => value !== domain);
      showRoutingRulesMessage("routingDomainRemoved", { domain });
      routingRulesChanged();
      renderRoutingRules();
    });

    item.append(domainText, remove);
    list.appendChild(item);
  }

  group.append(header, list);

  if (exit.available) {
    const add = document.createElement("button");
    add.type = "button";
    add.className = "routing-rule-add";
    add.textContent = t("routingAddSite");
    add.addEventListener("click", () => {
      openRoutingRuleEditor(exit.key, group, add);
    });
    group.appendChild(add);
  }

  return group;
}

function renderRoutingRules() {
  if (!routingRuleGroups) return;

  routingRuleGroups.replaceChildren(
    ...ROUTING_RULE_EXITS.map(createRoutingRuleGroup)
  );
}

function getRoutingRulesSelection({ focus = false } = {}) {
  const editorInput = routingRuleGroups
    ?.querySelector(".routing-rule-editor input");

  if (editorInput) {
    const domain = normalizeRoutingDomain(editorInput.value);

    if (!domain) {
      editorInput.setAttribute("aria-invalid", "true");
      showRoutingRulesMessage("routingFinishEditing", {}, true);

      if (focus) {
        profileSettings.open = true;
        editorInput.focus();
      }

      return null;
    }

    const exitKey = editorInput
      .closest(".routing-rule-group")
      ?.dataset.exit;

    if (!exitKey || !addRoutingDomain(exitKey, editorInput)) {
      return null;
    }
  }

  return Object.fromEntries(
    ROUTING_RULE_EXITS.map(exit => [
      exit.key,
      [...routingRulesByExit[exit.key]]
    ])
  );
}

function setRoutingRules(value = {}) {
  const source = value?.exits && typeof value.exits === "object"
    ? value.exits
    : value;

  const next = { riga: [], moscow: [], usa: [] };
  const seen = new Set();

  for (const exit of ROUTING_RULE_EXITS) {
    const domains = Array.isArray(source?.[exit.key])
      ? source[exit.key]
      : [];

    for (const rawDomain of domains) {
      const domain = normalizeRoutingDomain(rawDomain);
      if (domain && !seen.has(domain)) {
        next[exit.key].push(domain);
        seen.add(domain);
      }
    }

    next[exit.key].sort((left, right) => left.localeCompare(right));
  }

  routingRulesByExit = next;
  renderRoutingRules();
}

function resetRoutingRules() {
  setRoutingRules();
  showRoutingRulesMessage();
}

renderRoutingRules();
