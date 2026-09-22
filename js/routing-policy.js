// Routing preferences have their own revision and do not belong in profiles.
let routingAccount = null;
let routingEpoch = 0;
let routingRevision = null;
let routingDirty = false;
let routingSaving = false;
let routingLoading = false;
let routingConflict = false;
let routingTimer = null;
let routingStatusKey = "routingSignIn";
let routingRequest = 0;

function renderRoutingPolicyControls() {
  const busy = routingSaving || routingLoading || (typeof vpnBusy !== "undefined" && vpnBusy);
  const disabled = !routingAccount || routingRevision === null || busy;
  document.getElementById("routingRuleGroups")?.querySelectorAll("button, input")
    .forEach(control => { control.disabled = disabled; });
  const save = document.getElementById("routingPolicySave");
  const reload = document.getElementById("routingPolicyReload");
  const status = document.getElementById("routingPolicyStatus");
  if (save) save.disabled = disabled || !routingDirty || routingConflict;
  if (reload) reload.disabled = !routingAccount || busy;
  if (status) status.textContent = t(routingStatusKey);
}

function routingPolicyEdited() {
  routingDirty = true;
  routingStatusKey = routingConflict ? "routingConflict" : "routingUnsaved";
  renderRoutingPolicyControls();
}

function validateRoutingSnapshot(data) {
  if (!data || data.protocol !== 1 || !Number.isSafeInteger(data.revision) || data.revision < 0 ||
      !data.routingRules || !Array.isArray(data.availableExits)) throw new Error("Invalid routing response");
  for (const key of ["riga", "moscow", "usa"]) {
    if (!Array.isArray(data.routingRules[key]) || data.routingRules[key].some(domain =>
      typeof domain !== "string" || normalizeRoutingDomain(domain) !== domain)) {
      throw new Error("Invalid routing domains");
    }
  }
  return data;
}

function routingSnapshotStatus(data) {
  if (data.enforcementAvailable && data.state === "conflict") return "routingAddressConflict";
  if (data.enforcementAvailable && data.state === "unavailable") return "routingNodeUnavailable";
  if (data.state === "applied" && data.enforcementAvailable === true &&
      data.appliedRevision === data.revision) return "routingAppliedMoscow";
  if (data.state === "ready" && data.enforcementAvailable === true &&
      data.appliedRevision === data.revision) return "routingReadyMoscow";
  if (!data.revision) return "routingNotConfigured";
  return data.enforcementAvailable ? "routingPending" : "routingStoredOnly";
}

async function refreshRoutingPolicy({ discard = false } = {}) {
  if (!routingAccount || routingSaving || routingLoading) return;
  const epoch = routingEpoch;
  const request = ++routingRequest;
  routingLoading = discard || routingRevision === null;
  if (routingLoading) routingStatusKey = "routingLoading";
  renderRoutingPolicyControls();
  try {
    const data = validateRoutingSnapshot(await apiRequest("/vpn/routing-rules", {
      method: "GET", cache: "no-store"
    }));
    if (epoch !== routingEpoch || request !== routingRequest) return;
    if ((routingDirty || document.querySelector(".routing-rule-editor")) && !discard) {
      if (data.revision !== routingRevision) {
        routingConflict = true;
        routingStatusKey = "routingConflict";
      }
      return;
    }
    routingRevision = data.revision;
    routingConflict = false;
    routingDirty = false;
    for (const exit of ROUTING_RULE_EXITS) {
      exit.available = exit.key !== "usa" && data.availableExits.includes(exit.key);
    }
    setRoutingRules(data.routingRules);
    routingStatusKey = routingSnapshotStatus(data);
  } catch (error) {
    if (epoch !== routingEpoch || request !== routingRequest) return;
    routingStatusKey = routingDirty ? "routingDraftOffline" : "routingLoadFailed";
  } finally {
    if (epoch === routingEpoch && request === routingRequest) {
      routingLoading = false;
      renderRoutingPolicyControls();
    }
  }
}

async function saveRoutingPolicy() {
  if (!routingAccount || routingRevision === null || routingSaving || routingLoading || routingConflict) return;
  const rules = getRoutingRulesSelection({ focus: true });
  if (!rules) return;
  const epoch = routingEpoch;
  ++routingRequest; // An older status GET must not replace the POST result.
  routingSaving = true;
  routingStatusKey = "routingSaving";
  renderRoutingPolicyControls();
  try {
    const data = validateRoutingSnapshot(await apiRequest("/vpn/routing-rules", {
      method: "POST", body: JSON.stringify({ revision: routingRevision, routingRules: rules })
    }));
    if (epoch !== routingEpoch) return;
    routingRevision = data.revision;
    routingDirty = false;
    routingConflict = false;
    setRoutingRules(data.routingRules);
    routingStatusKey = routingSnapshotStatus(data);
  } catch (error) {
    if (epoch !== routingEpoch) return;
    routingConflict = error.status === 409;
    routingStatusKey = routingConflict ? "routingConflict" : "routingSaveFailed";
  } finally {
    if (epoch === routingEpoch) {
      routingSaving = false;
      renderRoutingPolicyControls();
    }
  }
}

function setRoutingAccount(username) {
  if (username && username === routingAccount) return;
  ++routingEpoch;
  ++routingRequest;
  clearInterval(routingTimer);
  routingTimer = null;
  routingAccount = username || null;
  routingRevision = null;
  routingDirty = routingSaving = routingLoading = routingConflict = false;
  routingStatusKey = username ? "routingLoading" : "routingSignIn";
  resetRoutingRules();
  renderRoutingPolicyControls();
  if (routingAccount) {
    refreshRoutingPolicy();
    routingTimer = setInterval(() => {
      if (!document.hidden && !document.querySelector(".routing-rule-editor")) refreshRoutingPolicy();
    }, 10000);
  }
}

document.getElementById("routingPolicySave")?.addEventListener("click", saveRoutingPolicy);
document.getElementById("routingPolicyReload")?.addEventListener("click", () => refreshRoutingPolicy({ discard: true }));
renderRoutingPolicyControls();
