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

function renderInvitation() {
  invitationCard.classList.toggle("hidden", !vpnInvitation && !invitationMessageKey && !invitationProtected);
  const conflict = Boolean(invitationAccount?.vpn?.configured);
  const key = invitationMessageKey || (vpnInvitation
    ? (!invitationAccount ? "inviteSignIn" : conflict ? "inviteConflict" : "inviteReady")
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
      unsupported_credential_file:"inviteUnavailable"
    };
    invitationMessageKey = errors[error.message] || "inviteRetry";
  } finally {
    invitationBusy = false;
    renderInvitation();
  }
});
