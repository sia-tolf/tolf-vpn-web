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

let currentLanguage = localStorage.getItem("tolfLanguage");

if (!["en", "ru", "lv"].includes(currentLanguage)) {
  const browserLanguage = navigator.language.toLowerCase();

  currentLanguage = browserLanguage.startsWith("ru")
    ? "ru"
    : browserLanguage.startsWith("lv")
      ? "lv"
      : "en";
}

const tolfUserAgent = navigator.userAgent || "";
const tolfNavigatorPlatform = navigator.platform || "";

const isTolfIPadDevice =
  navigator.maxTouchPoints > 1 &&
  !/Android|Windows/i.test(tolfUserAgent) &&
  (
    /iPad|Macintosh|Mac OS X/i.test(tolfUserAgent) ||
    /iPad|Mac/i.test(tolfNavigatorPlatform)
  );

let currentPlatform = localStorage.getItem("tolfPlatform");

if (isTolfIPadDevice) {
  currentPlatform = "ios";
  localStorage.setItem("tolfPlatform", "ios");
} else if (!["ios", "android", "windows"].includes(currentPlatform)) {
  currentPlatform = /Android/i.test(tolfUserAgent)
    ? "android"
    : /Windows NT/i.test(tolfUserAgent) ? "windows" : "ios";
}

let lastVpnState = null;
let lastPasskeys = [];
let allowedServers = ["riga"];
let promoRedeemed = false;
let promoPending = false;
let vpnBusy = false;
