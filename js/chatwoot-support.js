(() => {
  const endpoint = "https://api.tolf.is/support/widget";
  const language = () => {
    const query = new URLSearchParams(location.search).get("lang");
    if (["en", "ru", "lv"].includes(query)) return query;
    try {
      const saved = localStorage.getItem("tolfLanguage");
      if (["en", "ru", "lv"].includes(saved)) return saved;
    } catch {}
    return ["en", "ru", "lv"].includes(document.documentElement.lang)
      ? document.documentElement.lang : "en";
  };

  fetch(endpoint, { credentials: "include", cache: "no-store" })
    .then((response) => response.ok ? response.json() : null)
    .then((settings) => {
      if (!settings?.enabled || !settings.websiteToken ||
          settings.baseUrl !== "https://app.chatwoot.com") return;

      window.chatwootSettings = {
        locale: language(),
        useBrowserLanguage: false,
        position: "right",
        darkMode: "auto"
      };
      window.addEventListener("chatwoot:ready", () => {
        const identity = settings.identity;
        if (identity?.identifier && identity.identifierHash) {
          window.$chatwoot.setUser(identity.identifier, {
            name: identity.name || undefined,
            identifier_hash: identity.identifierHash
          });
        }
      }, { once: true });

      const sdk = document.createElement("script");
      sdk.src = settings.baseUrl + "/packs/js/sdk.js";
      sdk.async = true;
      sdk.onload = () => {
        window.chatwootSDK.run({
          websiteToken: settings.websiteToken,
          baseUrl: settings.baseUrl
        });
      };
      document.head.appendChild(sdk);
    })
    .catch(() => {});
})();
