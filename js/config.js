const API = "https://api.tolf.is";

const SERVERS = {
  riga: { host: "ikev2-riga.tolf.is", nameKey: "rigaLatvia" },
  moscow: { host: "", nameKey: "moscowRussia" },
  uk: { host: "", nameKey: "londonUk" }
};

const I18N = {};

let currentLanguage = localStorage.getItem("tolfLanguage");
if (currentLanguage !== "en" && currentLanguage !== "ru") {
  currentLanguage = navigator.language.toLowerCase().startsWith("ru") ? "ru" : "en";
}

let lastVpnState = null;
let lastPasskeys = [];
