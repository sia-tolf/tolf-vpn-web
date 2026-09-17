const API = "https://api.tolf.is";

const copy = {
  en: {
    account: "TOLF Account",
    signInTitle: "Sign in to TOLF",
    signInDescription: "Use your Passkey to access your TOLF account.",
    signIn: "Sign in with Passkey",
    createAccount: "Create account",
    recoverAccount: "Recover account",
    signupTitle: "Create your TOLF account",
    signupDescription: "Create a Passkey for this device. You will receive a recovery code after registration.",
    passkeyName: "Passkey name",
    passkeyHelp: "Use a short name that helps you recognize this device or key.",
    createPasskey: "Create Passkey",
    back: "Back",
    recoverTitle: "Recover your TOLF account",
    recoverDescription: "Enter your recovery code. A new Passkey and a new recovery code will be created.",
    recoveryCode: "Recovery code",
    recoverAction: "Recover account",
    saveRecoveryTitle: "Save your recovery code",
    saveRecoveryDescription: "Store this code somewhere safe. It can be used to recover your account if you lose your Passkey.",
    copyCode: "Copy code",
    savedContinue: "I saved it — continue",
    backHome: "← Back to TOLF",
    waitingPasskey: "Waiting for Passkey…",
    creatingPasskey: "Creating Passkey…",
    checkingRecovery: "Checking recovery code…",
    passkeyNotProvided: "Passkey was not provided.",
    passkeyNotCreated: "Passkey was not created.",
    passkeyNameRequired: "Enter a Passkey name of up to 80 characters.",
    passkeyNamingUnavailable: "Passkey naming is temporarily unavailable.",
    recoveryRequired: "Enter your recovery code.",
    recoveryCodeMissing: "Recovery code was not returned by the server.",
    copyDone: "Recovery code copied.",
    copyFailed: "Could not copy the recovery code.",
    signingInAfterRegistration: "Registration complete. Sign in once to continue.",
    unsupported: "This browser does not support Passkeys.",
    requestFailed: "Request failed"
  },
  ru: {
    account: "Аккаунт TOLF",
    signInTitle: "Вход в TOLF",
    signInDescription: "Используйте Passkey для входа в аккаунт TOLF.",
    signIn: "Войти с Passkey",
    createAccount: "Создать аккаунт",
    recoverAccount: "Восстановить аккаунт",
    signupTitle: "Создание аккаунта TOLF",
    signupDescription: "Создайте Passkey для этого устройства. После регистрации вы получите код восстановления.",
    passkeyName: "Имя Passkey",
    passkeyHelp: "Короткое имя поможет понять, какому устройству или ключу принадлежит Passkey.",
    createPasskey: "Создать Passkey",
    back: "Назад",
    recoverTitle: "Восстановление аккаунта TOLF",
    recoverDescription: "Введите код восстановления. Будут созданы новый Passkey и новый код восстановления.",
    recoveryCode: "Код восстановления",
    recoverAction: "Восстановить аккаунт",
    saveRecoveryTitle: "Сохраните код восстановления",
    saveRecoveryDescription: "Сохраните этот код в надёжном месте. Он понадобится, если доступ к Passkey будет потерян.",
    copyCode: "Скопировать код",
    savedContinue: "Я сохранил — продолжить",
    backHome: "← Назад в TOLF",
    waitingPasskey: "Ожидание Passkey…",
    creatingPasskey: "Создание Passkey…",
    checkingRecovery: "Проверка кода восстановления…",
    passkeyNotProvided: "Passkey не был предоставлен.",
    passkeyNotCreated: "Passkey не был создан.",
    passkeyNameRequired: "Введите имя Passkey длиной до 80 символов.",
    passkeyNamingUnavailable: "Имена Passkey временно недоступны.",
    recoveryRequired: "Введите код восстановления.",
    recoveryCodeMissing: "Сервер не вернул код восстановления.",
    copyDone: "Код восстановления скопирован.",
    copyFailed: "Не удалось скопировать код восстановления.",
    signingInAfterRegistration: "Регистрация завершена. Для продолжения войдите один раз.",
    unsupported: "Этот браузер не поддерживает Passkey.",
    requestFailed: "Ошибка запроса"
  },
  lv: {
    account: "TOLF konts",
    signInTitle: "Pieteikšanās TOLF",
    signInDescription: "Izmantojiet Passkey, lai piekļūtu savam TOLF kontam.",
    signIn: "Pieteikties ar Passkey",
    createAccount: "Izveidot kontu",
    recoverAccount: "Atjaunot kontu",
    signupTitle: "Izveidojiet TOLF kontu",
    signupDescription: "Izveidojiet Passkey šai ierīcei. Pēc reģistrācijas saņemsiet atkopšanas kodu.",
    passkeyName: "Passkey nosaukums",
    passkeyHelp: "Izmantojiet īsu nosaukumu, lai atpazītu šo ierīci vai atslēgu.",
    createPasskey: "Izveidot Passkey",
    back: "Atpakaļ",
    recoverTitle: "TOLF konta atjaunošana",
    recoverDescription: "Ievadiet atkopšanas kodu. Tiks izveidots jauns Passkey un jauns atkopšanas kods.",
    recoveryCode: "Atkopšanas kods",
    recoverAction: "Atjaunot kontu",
    saveRecoveryTitle: "Saglabājiet atkopšanas kodu",
    saveRecoveryDescription: "Saglabājiet šo kodu drošā vietā. Tas būs vajadzīgs, ja zaudēsiet piekļuvi Passkey.",
    copyCode: "Kopēt kodu",
    savedContinue: "Esmu saglabājis — turpināt",
    backHome: "← Atpakaļ uz TOLF",
    waitingPasskey: "Gaida Passkey…",
    creatingPasskey: "Izveido Passkey…",
    checkingRecovery: "Pārbauda atkopšanas kodu…",
    passkeyNotProvided: "Passkey netika nodrošināts.",
    passkeyNotCreated: "Passkey netika izveidots.",
    passkeyNameRequired: "Ievadiet Passkey nosaukumu līdz 80 rakstzīmēm.",
    passkeyNamingUnavailable: "Passkey nosaukumi pašlaik nav pieejami.",
    recoveryRequired: "Ievadiet atkopšanas kodu.",
    recoveryCodeMissing: "Serveris neatgrieza atkopšanas kodu.",
    copyDone: "Atkopšanas kods nokopēts.",
    copyFailed: "Neizdevās nokopēt atkopšanas kodu.",
    signingInAfterRegistration: "Reģistrācija pabeigta. Lai turpinātu, vienreiz piesakieties.",
    unsupported: "Šī pārlūkprogramma neatbalsta Passkey.",
    requestFailed: "Pieprasījuma kļūda"
  }
};

const panels = {
  signin: document.getElementById("signInPanel"),
  signup: document.getElementById("signupPanel"),
  recover: document.getElementById("recoverPanel"),
  recovery: document.getElementById("recoveryCodePanel")
};

const langButtons = {
  en: document.getElementById("langEn"),
  ru: document.getElementById("langRu"),
  lv: document.getElementById("langLv")
};

const signInButton = document.getElementById("signInButton");
const goSignupButton = document.getElementById("goSignupButton");
const goRecoverButton = document.getElementById("goRecoverButton");
const signupButton = document.getElementById("signupButton");
const signupBackButton = document.getElementById("signupBackButton");
const recoverButton = document.getElementById("recoverButton");
const recoverBackButton = document.getElementById("recoverBackButton");
const copyRecoveryButton = document.getElementById("copyRecoveryButton");
const continueButton = document.getElementById("continueButton");
const passkeyName = document.getElementById("passkeyName");
const recoveryCode = document.getElementById("recoveryCode");
const newRecoveryCode = document.getElementById("newRecoveryCode");
const backHome = document.getElementById("backHome");

const url = new URL(window.location.href);
const requestedLang = url.searchParams.get("lang");
const requestedMode = url.searchParams.get("mode");
const next = url.searchParams.get("next") === "vpn" ? "vpn" : "home";

let language = ["en", "ru", "lv"].includes(requestedLang)
  ? requestedLang
  : localStorage.getItem("tolf-language") || localStorage.getItem("tolfLanguage");

if (!["en", "ru", "lv"].includes(language)) {
  const browser = navigator.language.toLowerCase();
  language = browser.startsWith("ru") ? "ru" : browser.startsWith("lv") ? "lv" : "en";
}

let currentMode = ["signin", "signup", "recover"].includes(requestedMode)
  ? requestedMode
  : "signin";

function text(key) {
  return copy[language]?.[key] || copy.en[key] || key;
}

function destination() {
  const base = next === "vpn" ? "https://vpn.tolf.is/" : "https://tolf.is/";
  const target = new URL(base);
  target.searchParams.set("lang", language);
  return target.toString();
}

function setLanguage(nextLanguage) {
  if (!["en", "ru", "lv"].includes(nextLanguage)) return;
  language = nextLanguage;
  document.documentElement.lang = language;
  localStorage.setItem("tolf-language", language);
  localStorage.setItem("tolfLanguage", language);

  document.querySelectorAll("[data-i18n]").forEach(element => {
    element.textContent = text(element.dataset.i18n);
  });

  Object.entries(langButtons).forEach(([key, button]) => {
    button.classList.toggle("active", key === language);
    button.setAttribute("aria-pressed", key === language ? "true" : "false");
  });

  backHome.href = `https://tolf.is/?lang=${encodeURIComponent(language)}`;

  const nextUrl = new URL(window.location.href);
  nextUrl.searchParams.set("lang", language);
  history.replaceState(null, "", nextUrl.pathname + nextUrl.search);
}

function setMode(mode, updateUrl = true) {
  currentMode = mode;
  Object.entries(panels).forEach(([key, panel]) => {
    panel.classList.toggle("hidden", key !== mode);
  });

  if (updateUrl && mode !== "recovery") {
    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.set("mode", mode);
    history.replaceState(null, "", nextUrl.pathname + nextUrl.search);
  }

  if (mode === "signup") requestAnimationFrame(() => passkeyName.focus());
  if (mode === "recover") requestAnimationFrame(() => recoveryCode.focus());
}

function setMessage(id, value = "", state = "") {
  const element = document.getElementById(id);
  element.textContent = value;
  element.className = `message${state ? ` ${state}` : ""}`;
}

function setBusy(busy) {
  [
    signInButton,
    goSignupButton,
    goRecoverButton,
    signupButton,
    signupBackButton,
    recoverButton,
    recoverBackButton,
    copyRecoveryButton,
    continueButton
  ].forEach(button => { button.disabled = busy; });
}

async function apiRequest(path, options = {}) {
  const response = await fetch(API + path, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  let data = null;
  try { data = await response.json(); } catch {}

  if (!response.ok) {
    throw new Error(data?.detail || text("requestFailed"));
  }
  return data;
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

async function startSignIn(messageId = "signInMessage") {
  if (!("PublicKeyCredential" in window)) {
    throw new Error(text("unsupported"));
  }

  setMessage(messageId, text("waitingPasskey"));
  const begin = await apiRequest("/passkey/login/begin", {
    method: "POST",
    body: "{}"
  });

  const credential = await navigator.credentials.get({
    publicKey: prepareAuthenticationOptions(begin.options)
  });

  if (!credential) throw new Error(text("passkeyNotProvided"));

  await apiRequest("/passkey/login/finish", {
    method: "POST",
    body: JSON.stringify({
      challengeId: begin.challengeId,
      credential: serializeCredential(credential)
    })
  });
}

async function alreadyAuthenticated() {
  try {
    await apiRequest("/me", { method: "GET" });
    return true;
  } catch {
    return false;
  }
}

async function finishAndLeave(messageId) {
  if (!(await alreadyAuthenticated())) {
    setMessage(messageId, text("signingInAfterRegistration"));
    await startSignIn(messageId);
  }
  window.location.assign(destination());
}

signInButton.addEventListener("click", async () => {
  setBusy(true);
  setMessage("signInMessage");
  try {
    await startSignIn("signInMessage");
    window.location.assign(destination());
  } catch (error) {
    setMessage("signInMessage", error.message, "error");
  } finally {
    setBusy(false);
  }
});

goSignupButton.addEventListener("click", () => {
  setMessage("signInMessage");
  setMode("signup");
});

goRecoverButton.addEventListener("click", () => {
  setMessage("signInMessage");
  setMode("recover");
});

signupBackButton.addEventListener("click", () => {
  setMessage("signupMessage");
  setMode("signin");
});

recoverBackButton.addEventListener("click", () => {
  recoveryCode.value = "";
  setMessage("recoverMessage");
  setMode("signin");
});

signupButton.addEventListener("click", async () => {
  const name = passkeyName.value.trim();
  if (!name || name.length > 80 || /[\u0000-\u001f\u007f-\u009f]/.test(name)) {
    setMessage("signupMessage", text("passkeyNameRequired"), "error");
    passkeyName.focus();
    return;
  }

  setBusy(true);
  setMessage("signupMessage", text("creatingPasskey"));

  try {
    if (!("PublicKeyCredential" in window)) throw new Error(text("unsupported"));

    const naming = await apiRequest("/passkeys/naming", { method: "GET" });
    if (naming?.version !== 1) throw new Error(text("passkeyNamingUnavailable"));

    const begin = await apiRequest("/passkey/register/begin", {
      method: "POST",
      body: JSON.stringify({ passkeyName: name })
    });

    const credential = await navigator.credentials.create({
      publicKey: prepareRegistrationOptions(begin.options)
    });

    if (!credential) throw new Error(text("passkeyNotCreated"));

    const finish = await apiRequest("/passkey/register/finish", {
      method: "POST",
      body: JSON.stringify({
        challengeId: begin.challengeId,
        credential: serializeCredential(credential)
      })
    });

    if (!finish?.recoveryCode) throw new Error(text("recoveryCodeMissing"));

    newRecoveryCode.textContent = finish.recoveryCode;
    setMessage("recoveryCodeMessage");
    setMode("recovery", false);
  } catch (error) {
    setMessage("signupMessage", error.message, "error");
  } finally {
    setBusy(false);
  }
});

recoverButton.addEventListener("click", async () => {
  const code = recoveryCode.value.trim().toUpperCase();
  if (!code) {
    setMessage("recoverMessage", text("recoveryRequired"), "error");
    recoveryCode.focus();
    return;
  }

  setBusy(true);
  setMessage("recoverMessage", text("checkingRecovery"));

  try {
    if (!("PublicKeyCredential" in window)) throw new Error(text("unsupported"));

    const begin = await apiRequest("/recovery/begin", {
      method: "POST",
      body: JSON.stringify({ recoveryCode: code })
    });

    const credential = await navigator.credentials.create({
      publicKey: prepareRegistrationOptions(begin.options)
    });

    if (!credential) throw new Error(text("passkeyNotCreated"));

    const finish = await apiRequest("/recovery/finish", {
      method: "POST",
      body: JSON.stringify({
        challengeId: begin.challengeId,
        credential: serializeCredential(credential)
      })
    });

    if (!finish?.recoveryCode) throw new Error(text("recoveryCodeMissing"));

    recoveryCode.value = "";
    newRecoveryCode.textContent = finish.recoveryCode;
    setMessage("recoveryCodeMessage");
    setMode("recovery", false);
  } catch (error) {
    setMessage("recoverMessage", error.message, "error");
  } finally {
    setBusy(false);
  }
});

copyRecoveryButton.addEventListener("click", async () => {
  const code = newRecoveryCode.textContent.trim();
  if (!code) return;
  try {
    await copyText(code);
    setMessage("recoveryCodeMessage", text("copyDone"), "success");
  } catch {
    setMessage("recoveryCodeMessage", text("copyFailed"), "error");
  }
});

continueButton.addEventListener("click", async () => {
  setBusy(true);
  setMessage("recoveryCodeMessage");
  try {
    await finishAndLeave("recoveryCodeMessage");
  } catch (error) {
    setMessage("recoveryCodeMessage", error.message, "error");
  } finally {
    setBusy(false);
  }
});

Object.entries(langButtons).forEach(([lang, button]) => {
  button.addEventListener("click", () => setLanguage(lang));
});

setLanguage(language);
setMode(currentMode, false);

alreadyAuthenticated().then(authenticated => {
  if (authenticated) window.location.replace(destination());
});
