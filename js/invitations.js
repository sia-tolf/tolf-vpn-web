// The bearer invitation stays in the fragment/session storage, never in a query string.
let vpnInvitation = "";
let invitationAccount = null;
let invitationBusy = false;
let invitationProtected = false;
let invitationMessageKey = "";
let invitationUsername = "";
const invitationKey = "tolfExistingVpnInvitation";
const invitationFragment = new URLSearchParams(location.hash.slice(1));
const incomingInvitation = invitationFragment.get("invite");
try { vpnInvitation = sessionStorage.getItem(invitationKey) || ""; } catch {}
if (incomingInvitation !== null) {
  vpnInvitation = /^[A-Za-z0-9_-]{43}$/.test(incomingInvitation) ? incomingInvitation : "";
  invitationMessageKey = vpnInvitation ? "" : "inviteInvalid";
  try {
    if (vpnInvitation) sessionStorage.setItem(invitationKey, vpnInvitation);
    else sessionStorage.removeItem(invitationKey);
  } catch {}
  history.replaceState(null, "", location.pathname + location.search);
}
const invitationCard = document.getElementById("invitationCard");
const invitationText = document.getElementById("invitationText");
const invitationButton = document.getElementById("invitationButton");
const invitationDismiss = document.getElementById("invitationDismiss");

let existingVpnChecked = false;
let existingVpnSupported = false;
let existingVpnChecking = false;
let existingVpnMessageKey = "";
const existingVpnCard = document.getElementById("existingVpnCard");
const existingVpnForm = document.getElementById("existingVpnForm");
const existingVpnPassword = document.getElementById("existingVpnPassword");

function renderExistingVpn() {
  existingVpnCard.classList.toggle("hidden", !existingVpnChecked || Boolean(invitationAccount?.vpn?.configured) || Boolean(vpnInvitation));
  document.getElementById("existingVpnSubmit").disabled = existingVpnChecking || !existingVpnSupported;
  document.getElementById("existingVpnSubmit").textContent = t(existingVpnChecking ? "existingVpnChecking" : "existingVpnVerify");
  document.getElementById("existingVpnMessage").textContent = t(existingVpnMessageKey || (!existingVpnSupported ? "existingVpnUnavailable" : "existingVpnPrivate"));
}

apiRequest("/vpn/invitations/capabilities", {method:"GET"}).then(data => {
  existingVpnSupported = data.passwordLinking === true;
  renderExistingVpn();
}).catch(() => renderExistingVpn());

existingVpnForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (existingVpnChecking || !existingVpnSupported || vpnInvitation) return;
  const username = document.getElementById("existingVpnUsername").value.trim();
  let password = existingVpnPassword.value;
  existingVpnPassword.value = "";
  existingVpnChecking = true;
  existingVpnMessageKey = "";
  renderExistingVpn();
  try {
    const result = await apiRequest("/vpn/invitations/verify", {
      method:"POST", body:JSON.stringify({username,password})
    });
    vpnInvitation = result.token;
    invitationUsername = result.username;
    invitationMessageKey = "";
    try { sessionStorage.setItem(invitationKey,vpnInvitation); } catch {}
    document.getElementById("existingVpnUsername").value = "";
    renderInvitation();
    invitationCard.scrollIntoView({block:"center"});
  } catch (error) {
    const keys = {invalid_credentials:"existingVpnInvalid", admin_invitation_required:"existingVpnAdmin",
      too_many_attempts:"existingVpnLimited", already_linked:"existingVpnLinked"};
    existingVpnMessageKey = keys[error.message] || "existingVpnUnavailable";
  } finally {
    password = "";
    existingVpnPassword.value = "";
    existingVpnChecking = false;
    renderExistingVpn();
  }
});

function renderInvitation() {
  renderExistingVpn();
  const nameInput = document.getElementById("registerPasskeyName");
  if (nameInput && !nameInput.dataset.edited) nameInput.value = invitationUsername || "";
  const linkingSignIn = Boolean(vpnInvitation && !invitationAccount);
  document.getElementById("inviteSetupHelp").classList.toggle("hidden", !linkingSignIn);
  createAccountButton.textContent = t(linkingSignIn ? "inviteCreatePasskey" : "createNewAccount");
  signInButton.textContent = t(linkingSignIn ? "inviteExistingPasskey" : "signInWithPasskey");
  createAccountButton.classList.toggle("primary", linkingSignIn);
  createAccountButton.classList.toggle("secondary", !linkingSignIn);
  signInButton.classList.toggle("primary", !linkingSignIn);
  signInButton.classList.toggle("secondary", linkingSignIn);
  invitationCard.classList.toggle("hidden", !vpnInvitation && !invitationMessageKey && !invitationProtected);
  const conflict = Boolean(invitationAccount?.vpn?.configured);
  const key = invitationMessageKey || (vpnInvitation
    ? (!invitationAccount ? (invitationUsername ? "existingVpnVerifiedSignIn" : "inviteSignIn") : conflict ? "inviteConflict" : (invitationUsername ? "existingVpnVerifiedReady" : "inviteReady"))
    : "inviteProtected");
  invitationText.textContent = t(key, {username: invitationUsername});
  invitationButton.classList.toggle("hidden", !vpnInvitation || !invitationAccount || conflict);
  invitationButton.disabled = invitationBusy;
  invitationButton.textContent = t(invitationBusy ? "inviteWorking" : "inviteAccept");
  invitationDismiss.classList.toggle("hidden", !vpnInvitation);
  invitationDismiss.disabled = invitationBusy;
  // Server enforces this protection too, before deleting any Windows devices.
  deleteVpnButton.classList.toggle("hidden", invitationProtected);
  deleteAccountButton.classList.toggle("hidden", invitationProtected);
}

async function updateInvitationAccount(data) {
  existingVpnChecked = true;
  invitationAccount = data;
  invitationProtected = false;
  if (data) {
    try {
      const status = await apiRequest("/vpn/invitations/status", {method:"GET"});
      invitationProtected = status.protected === true;
      if (status.pending && !vpnInvitation) invitationMessageKey = "invitePending";
    } catch { /* Backend deployment can follow the website deployment. */ }
  }
  renderInvitation();
}

invitationDismiss.addEventListener("click", () => {
  vpnInvitation = "";
  invitationMessageKey = "";
  try { sessionStorage.removeItem(invitationKey); } catch {}
  renderInvitation();
});

invitationButton.addEventListener("click", async () => {
  if (invitationBusy || !vpnInvitation || !invitationAccount) return;
  invitationBusy = true;
  renderInvitation();
  try {
    const result = await apiRequest("/vpn/invitations/claim", {
      method:"POST", body:JSON.stringify({token:vpnInvitation})
    });
    invitationUsername = result.username;
    vpnInvitation = "";
    try { sessionStorage.removeItem(invitationKey); } catch {}
    invitationMessageKey = "inviteSuccess";
    await loadAccount();
  } catch (error) {
    const errors = {
      invalid_invitation:"inviteInvalid", invitation_expired:"inviteInvalid",
      invitation_used:"inviteInvalid", account_has_vpn:"inviteConflict",
      already_linked:"inviteConflict", user_not_found:"inviteUnavailable",
      unsupported_credential_file:"inviteUnavailable", admin_invitation_required:"existingVpnAdmin",
      pending_invitation:"invitePending"
    };
    invitationMessageKey = errors[error.message] || "inviteRetry";
  } finally {
    invitationBusy = false;
    renderInvitation();
  }
});

document.getElementById("registerPasskeyName").addEventListener("input", (event) => { event.target.dataset.edited = "1"; });
