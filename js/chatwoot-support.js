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
      let notice = null;
      const mountNotice = () => {
        const holder = document.getElementById("cw-widget-holder");
        if (!holder || notice) return;
        const style = document.createElement("style");
        style.textContent = `
          #cw-widget-holder.tolf-support-notice-mounted:not(.has-unread-view) {
            display: flex !important;
            flex-direction: column !important;
          }
          #cw-widget-holder.tolf-support-notice-mounted:not(.has-unread-view) iframe {
            flex: 1 1 0 !important;
            min-height: 0 !important;
            height: 0 !important;
          }
          #cw-widget-holder .tolf-support-language-notice {
            flex: 0 0 auto;
            margin: 0;
            padding: 12px 16px;
            background: #f4f7fc;
            color: #263e61;
            border-bottom: 1px solid #e0e6ef;
            font: 500 13px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            text-align: center;
          }
          #cw-widget-holder.has-unread-view .tolf-support-language-notice { display: none; }
          @media (prefers-color-scheme: dark) {
            #cw-widget-holder .tolf-support-language-notice {
              background: #202630;
              color: #e0e9f7;
              border-color: #394353;
            }
          }
        `;
        document.head.appendChild(style);
        notice = document.createElement("p");
        notice.className = "tolf-support-language-notice";
        notice.textContent = supportDescription[language()];
        notice.lang = language();
        holder.prepend(notice);
        holder.classList.add("tolf-support-notice-mounted");
      };
      let ready = false;
      let appliedLocale = null;
      const syncLocale = () => {
        const locale = language();
        const description = supportDescription[locale];
        if (notice) {
          notice.textContent = description;
          notice.lang = locale;
        }
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
        mountNotice();
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
