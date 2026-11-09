(() => {
  const supportDescription = {
    ru: "Мы принимаем сообщения на английском или русском языке.",
    en: "We accept messages in English or Russian.",
    lv: "Mēs pieņemam ziņojumus angļu vai krievu valodā."
  };
  const endpoint = "https://api.tolf.is/support/widget";
  const language = () => {
    const active = document.documentElement.lang;
    if (["en", "ru", "lv"].includes(active)) return active;
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
        welcomeDescription: supportDescription[language()],
        useBrowserLanguage: false,
        position: "right",
        darkMode: "auto"
      };
      let ready = false;
      let appliedLocale = null;
      const syncLocale = () => {
        const locale = language();
        const description = supportDescription[locale];
        window.chatwootSettings.locale = locale;
        window.chatwootSettings.welcomeDescription = description;
        if (ready && locale !== appliedLocale) {
          const widget = window.$chatwoot;
          widget.locale = locale;
          widget.welcomeDescription = description;
          widget.setLocale(locale);
          // Refresh custom copy through the widget's existing configuration channel.
          // Keep the SDK's current appearance and feature settings intact.
          const frame = document.getElementById("chatwoot_live_chat_widget");
          const config = { event: "config-set", locale };
          for (const key of [
            "position", "hideMessageBubble", "showPopoutButton", "widgetStyle",
            "darkMode", "showUnreadMessagesDialog", "welcomeTitle",
            "welcomeDescription", "availableMessage", "unavailableMessage",
            "enableFileUpload", "enableEmojiPicker", "enableEndConversation"
          ]) config[key] = widget[key];
          frame?.contentWindow?.postMessage(
            "chatwoot-widget:" + JSON.stringify(config), settings.baseUrl
          );
          appliedLocale = locale;
        }
      };
      new MutationObserver(syncLocale).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["lang"]
      });
      window.addEventListener("chatwoot:ready", () => {
        ready = true;
        syncLocale();
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
