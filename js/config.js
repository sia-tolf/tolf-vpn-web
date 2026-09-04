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

let currentLanguage = localStorage.getItem("tolfLanguage");

if (!["en", "ru", "lv"].includes(currentLanguage)) {
  const browserLanguage = navigator.language.toLowerCase();

  currentLanguage = browserLanguage.startsWith("ru")
    ? "ru"
    : browserLanguage.startsWith("lv")
      ? "lv"
      : "en";
}

let currentPlatform = localStorage.getItem("tolfPlatform");

if (currentPlatform !== "ios" && currentPlatform !== "android") {
  currentPlatform = "ios";
}

let lastVpnState = null;
let lastPasskeys = [];
let allowedServers = ["riga"];
let promoRedeemed = false;
let promoPending = false;
let vpnBusy = false;
