const API = "https://api.tolf.is";

const SERVERS = {
  us: { host: "ikev2-us.tolf.is", nameKey: "cityNewYork" },
  riga: { host: "ikev2-riga.tolf.is", nameKey: "rigaLatvia" },
  moscow: { host: "ikev2.tolf.is", nameKey: "moscowRussia" },
  uk: { host: "", nameKey: "londonUk" }
};

const I18N = {};

const LOCAL_ID_OPTIONS = {
  us: { auto: "routingUsAuto", ru: "routingRu", lv: "routingLv", yt: "routingUsYt" },
  riga: { sr: "routingRigaSr", ru: "routingRu", yt: "routingYt" },
  moscow: {
    "": "routingMoscowDefault",
    sr: "routingMoscowSr",
    ru: "routingRu",
    lv: "routingLv",
    yt: "routingYt"
  }
};

const LOCAL_ID_DEFAULTS = {
  us: "auto",
  riga: "sr",
  moscow: ""
};

let localIdValues = {
  us: "",
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

// Restore the user's selected platform; detect the device only on the first visit.
let savedPlatform = null;
try { savedPlatform = localStorage.getItem("tolfPlatform"); } catch {}
let currentPlatform = ["ios", "android", "windows"].includes(savedPlatform)
  ? savedPlatform
  : /Windows NT/i.test(tolfUserAgent)
    ? "windows"
    : /Android/i.test(tolfUserAgent)
      ? "android"
      : "ios";

try { localStorage.setItem("tolfPlatform", currentPlatform); } catch {}

let lastVpnState = null;
let lastPasskeys = [];
let allowedServers = ["riga"];
let promoRedeemed = false;
let promoPending = false;
let vpnBusy = false;
