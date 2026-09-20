const API = "https://api.tolf.is";

const SERVERS = {
  riga: { host: "ikev2-riga.tolf.is", nameKey: "rigaLatvia" },
  moscow: { host: "ikev2.tolf.is", nameKey: "moscowRussia" },
  uk: { host: "", nameKey: "londonUk" }
};

const I18N = {};

const LOCAL_ID_OPTIONS = {
  riga: { sr: "routingRigaSr", ru: "routingRu" },
  moscow: {
    "": "routingMoscowDefault",
    sr: "routingMoscowSr",
    ru: "routingRu",
    lv: "routingLv"
  }
};

const LOCAL_ID_DEFAULTS = {
  riga: "sr",
  moscow: ""
};

let localIdValues = {
  riga: "",
  moscow: ""
};

const ON_DEMAND_ACTIONS = [
  "Connect",
  "Disconnect",
  "Ignore"
];

const tolfRequestedLanguage =
  new URL(window.location.href).searchParams.get("lang");

let currentLanguage =
  ["en", "ru", "lv"].includes(tolfRequestedLanguage)
    ? tolfRequestedLanguage
    : localStorage.getItem("tolfLanguage");

if (!["en", "ru", "lv"].includes(currentLanguage)) {
  const browserLanguage = navigator.language.toLowerCase();

  currentLanguage = browserLanguage.startsWith("ru")
    ? "ru"
    : browserLanguage.startsWith("lv")
      ? "lv"
      : "en";
}

const tolfUserAgent = navigator.userAgent || "";

// Initial platform follows the physical device on every page load.
// Manual switching still works for the current session, but a stale saved
// Android/Windows choice must never make an iPad reopen as that platform.
let currentPlatform =
  /Windows NT/i.test(tolfUserAgent)
    ? "windows"
    : /Android/i.test(tolfUserAgent)
      ? "android"
      : "ios";

localStorage.setItem("tolfPlatform", currentPlatform);

let lastVpnState = null;
let lastPasskeys = [];
let allowedServers = ["riga"];
let promoRedeemed = false;
let promoPending = false;
let vpnBusy = false;
