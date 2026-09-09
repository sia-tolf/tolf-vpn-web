const loadingCard = document.getElementById("loadingCard");
const signedOutCard = document.getElementById("signedOutCard");
const vpnCard = document.getElementById("vpnCard");

const languageEn = document.getElementById("languageEn");
const languageRu = document.getElementById("languageRu");
const languageLv = document.getElementById("languageLv");

const platformIos = document.getElementById("platformIos");
const platformAndroid = document.getElementById("platformAndroid");

const signInButton = document.getElementById("signInButton");
const createAccountButton = document.getElementById("createAccountButton");
const showRecoverButton = document.getElementById("showRecoverButton");
const signedOutMainActions = document.getElementById("signedOutMainActions");

const recoverPanel = document.getElementById("recoverPanel");
const recoveryInput = document.getElementById("recoveryInput");
const recoverAccountButton = document.getElementById("recoverAccountButton");
const cancelRecoverButton = document.getElementById("cancelRecoverButton");

const signedOutRecoveryBox =
  document.getElementById("signedOutRecoveryBox");
const signedOutRecoveryCode =
  document.getElementById("signedOutRecoveryCode");
const copySignedOutRecoveryButton =
  document.getElementById("copySignedOutRecoveryButton");
const savedSignedOutRecoveryButton =
  document.getElementById("savedSignedOutRecoveryButton");

const signedOutMessage = document.getElementById("signedOutMessage");
const signOutButton = document.getElementById("signOutButton");

const serverSection = document.getElementById("serverSection");
const selectedServerAddress =
  document.getElementById("selectedServerAddress");
const serverInputs =
  document.querySelectorAll('input[name="vpnServer"]');

const vpnStatus = document.getElementById("vpnStatus");
const serverRow = document.getElementById("serverRow");
const vpnServerName = document.getElementById("vpnServerName");
const vpnServerHost = document.getElementById("vpnServerHost");
const usernameRow = document.getElementById("usernameRow");
const vpnUsername = document.getElementById("vpnUsername");

const createVpnButton = document.getElementById("createVpnButton");
const generateProfileButton =
  document.getElementById("generateProfileButton");
const installProfileButton =
  document.getElementById("installProfileButton");
const shareProfileButton =
  document.getElementById("shareProfileButton");
const profileDeliveryActions =
  document.getElementById("profileDeliveryActions");
const rotatePasswordButton =
  document.getElementById("rotatePasswordButton");
const rotatePasswordNote =
  document.getElementById("rotatePasswordNote");

const deleteSection = document.getElementById("deleteSection");
const deleteVpnButton = document.getElementById("deleteVpnButton");

const passkeyList = document.getElementById("passkeyList");
const addPasskeyButton = document.getElementById("addPasskeyButton");
const passkeyMessage = document.getElementById("passkeyMessage");

const generateRecoveryButton =
  document.getElementById("generateRecoveryButton");
const accountRecoveryBox =
  document.getElementById("accountRecoveryBox");
const accountRecoveryCode =
  document.getElementById("accountRecoveryCode");
const copyAccountRecoveryButton =
  document.getElementById("copyAccountRecoveryButton");
const savedAccountRecoveryButton =
  document.getElementById("savedAccountRecoveryButton");
const recoveryMessage = document.getElementById("recoveryMessage");

const deleteAccountButton =
  document.getElementById("deleteAccountButton");
const vpnMessage = document.getElementById("vpnMessage");

const promoInput = document.getElementById("promoInput");
const redeemPromoButton =
  document.getElementById("redeemPromoButton");
const promoForm = document.getElementById("promoForm");
const promoMessage = document.getElementById("promoMessage");
const promoGranted = document.getElementById("promoGranted");
const moscowAccessLabel =
  document.getElementById("moscowAccessLabel");

const profileSettings = document.getElementById("profileSettings");
const localIdInput = document.getElementById("localIdInput");
const localIdChoices = document.getElementById("localIdChoices");
const localIdRoutingHint =
  document.getElementById("localIdRoutingHint");
const dnsMode = document.getElementById("dnsMode");
const dnsCustomGroup = document.getElementById("dnsCustomGroup");
const dnsServersInput = document.getElementById("dnsServersInput");
const dnsValidation = document.getElementById("dnsValidation");

const onDemandSection = document.getElementById("onDemandSection");
const onDemandAndroidNote =
  document.getElementById("onDemandAndroidNote");
const onDemandEnabled = document.getElementById("onDemandEnabled");
const onDemandOptions = document.getElementById("onDemandOptions");
const alwaysOn = document.getElementById("alwaysOn");
const alwaysOnHint = document.getElementById("alwaysOnHint");
const manualOnDemandRules =
  document.getElementById("manualOnDemandRules");
const wifiAction = document.getElementById("wifiAction");
const cellularAction = document.getElementById("cellularAction");
const ethernetAction = document.getElementById("ethernetAction");
const onDemandRules = document.getElementById("onDemandRules");
const addOnDemandRule = document.getElementById("addOnDemandRule");

const latencyRiga = document.getElementById("latencyRiga");
const latencyMoscow = document.getElementById("latencyMoscow");

const connectionTestCard = document.getElementById("connectionTestCard");
const connectionTestTitle = document.getElementById("connectionTestTitle");
const connectionTestStatus = document.getElementById("connectionTestStatus");
const connectionTestLatency =
  document.getElementById("connectionTestLatency");
const connectionTestJitter =
  document.getElementById("connectionTestJitter");
const connectionTestDownload =
  document.getElementById("connectionTestDownload");
const connectionTestUpload =
  document.getElementById("connectionTestUpload");
const connectionTestButton =
  document.getElementById("connectionTestButton");

const networkMetrics = document.getElementById("networkMetrics");
const networkMetricLatency =
  document.getElementById("networkMetricLatency");
const networkMetricRigaToMoscow =
  document.getElementById("networkMetricRigaToMoscow");
const networkMetricMoscowToRiga =
  document.getElementById("networkMetricMoscowToRiga");
const networkMetricMeasuredAt =
  document.getElementById("networkMetricMeasuredAt");
