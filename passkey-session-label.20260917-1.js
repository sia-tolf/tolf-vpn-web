/* TOLF current Passkey label.
   Presentation-only helper: remembers the Passkey name used for a successful
   sign-in and exposes it to sibling TOLF sites through a first-party cookie.
   Authentication decisions continue to use the HttpOnly server session only. */
(() => {
  "use strict";

  const API = "https://api.tolf.is";
  const COOKIE = "tolf_current_passkey";
  const MAX_AGE = 30 * 24 * 60 * 60;
  const originalFetch = window.fetch.bind(window);

  function requestUrl(input) {
    try {
      return typeof input === "string" ? new URL(input, window.location.href).href : input?.url || "";
    } catch (_) {
      return "";
    }
  }

  function readLabel() {
    const prefix = `${COOKIE}=`;
    const part = document.cookie.split("; ").find(value => value.startsWith(prefix));
    if (!part) return "";
    try {
      return decodeURIComponent(part.slice(prefix.length)).trim().slice(0, 80);
    } catch (_) {
      return "";
    }
  }

  function writeLabel(value) {
    const name = typeof value === "string" ? value.trim().slice(0, 80) : "";
    if (!name) return;
    document.cookie = `${COOKIE}=${encodeURIComponent(name)}; Max-Age=${MAX_AGE}; Path=/; Domain=tolf.is; Secure; SameSite=Lax`;
  }

  function clearLabel() {
    document.cookie = `${COOKIE}=; Max-Age=0; Path=/; Domain=tolf.is; Secure; SameSite=Lax`;
    document.cookie = `${COOKIE}=; Max-Age=0; Path=/; Secure; SameSite=Lax`;
  }

  function loginCredentialId(init) {
    if (typeof init?.body !== "string") return "";
    try {
      const body = JSON.parse(init.body);
      const id = body?.credential?.id;
      return typeof id === "string" ? id : "";
    } catch (_) {
      return "";
    }
  }

  async function rememberPasskey(credentialId) {
    if (!credentialId) return;
    const response = await originalFetch(`${API}/passkeys`, {
      method: "GET",
      credentials: "include",
      cache: "no-store",
      headers: { Accept: "application/json" }
    });
    if (!response.ok) return;
    const data = await response.json();
    const item = Array.isArray(data?.passkeys)
      ? data.passkeys.find(passkey => passkey?.id === credentialId)
      : null;
    if (item?.name) writeLabel(item.name);
  }

  window.fetch = async function tolfFetch(input, init) {
    const url = requestUrl(input);
    const isLoginFinish = url === `${API}/passkey/login/finish`;
    const isLogout = url === `${API}/logout`;
    const isAccountDelete = url === `${API}/account/delete`;
    const isMe = url === `${API}/me`;
    const credentialId = isLoginFinish ? loginCredentialId(init) : "";

    const response = await originalFetch(input, init);

    if (response.ok && isLoginFinish) {
      try { await rememberPasskey(credentialId); } catch (_) {}
    }

    if (response.ok && (isLogout || isAccountDelete)) {
      clearLabel();
    }

    if (response.ok && isMe) {
      const label = readLabel();
      if (label) {
        try {
          const data = await response.clone().json();
          if (!data?.currentPasskey?.name) {
            data.currentPasskey = { name: label, source: "browser-session" };
            return new Response(JSON.stringify(data), {
              status: response.status,
              statusText: response.statusText,
              headers: { "Content-Type": "application/json" }
            });
          }
        } catch (_) {}
      }
    }

    return response;
  };
})();
