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

const passwordCopy = {
  "en": {
    "signInDescription": "Choose how to sign in to your TOLF account.",
    "signupDescription": "Choose a sign-in method. No email address or phone number is required.",
    "passwordMethod": "Username and password",
    "passkeyAbout": "Passkey is a convenient, phishing-resistant way to sign in without a password. It can be stored in Google Password Manager, 1Password, iCloud Keychain or Windows Hello, depending on your device and setup. If a suitable method is not available, choose username and password.",
    "usernameLabel": "Username",
    "passwordLabel": "Account password",
    "newPassword": "New account password",
    "usernameHelp": "Choose your own username: 3–32 Latin letters, numbers, dots, hyphens or underscores. Start with a letter or number. Uppercase and lowercase are treated the same. Example: lena-work.",
    "passwordHelp": "Use 15–128 characters. You can generate a password or enter your own; a generated password can also be edited.",
    "showPassword": "Show password",
    "hidePassword": "Hide password",
    "generatePassword": "Generate password",
    "passwordSignIn": "Sign in",
    "saveCredentialsHint": "Save your username and password in a password manager before continuing. This is your TOLF account password; VPN connection passwords are separate.",
    "resetHelp": "Enter the username you saved, your recovery code and a new password. Previous account sessions will be signed out. Your VPN profiles and existing Passkeys stay in place.",
    "passwordRecoverDescription": "Use the recovery code saved when you registered with a username and password.",
    "resetPassword": "Set new password",
    "saveRecoveryDescription": "Save this code in a safe place. It gives access to your account, so do not share it. We do not send it by email.",
    "recoveryInstructions": "If you lose access, open TOLF → Sign in → Recover account. Choose your sign-in method and enter this code; for password recovery, enter your username too. After recovery, save the new code: the old one will no longer work. If you lose both your sign-in credentials and this code, you cannot recover the account.",
    "downloadCredentials": "Download sign-in details",
    "savedAcknowledgement": "I have saved my sign-in details and recovery code.",
    "savingAccount": "Creating account…",
    "signingIn": "Signing in…",
    "savedRequired": "Save your sign-in details and code, then tick the checkbox.",
    "invalid_username": "Use 3–32 Latin letters, numbers, dots, hyphens or underscores, starting with a letter or number.",
    "invalid_password": "Use a password of 15–128 characters.",
    "weak_password": "Choose a less predictable password or generate one.",
    "username_taken": "This username is already taken. Choose another.",
    "invalid_credentials": "The username or password is incorrect.",
    "invalid_recovery": "The username or recovery code is incorrect, or the code has already been replaced.",
    "too_many_attempts": "Too many attempts. Try again in 15 minutes.",
    "try_later": "Please try again in a few seconds.",
    "invalid_origin": "Reload the TOLF sign-in page and try again.",
    "passwordUnavailable": "Password sign-in is temporarily unavailable. Please try again later.",
    "passwordSessionExpired": "Sign in again with your username and password. Your account has already been created.",
    "downloadNote": "Keep this file private. It contains account access details."
  },
  "ru": {
    "signInDescription": "Выберите способ входа в аккаунт TOLF.",
    "signupDescription": "Выберите способ входа. Электронная почта и номер телефона не нужны.",
    "passwordMethod": "Логин и пароль",
    "passkeyAbout": "Passkey — удобный вход без пароля с защитой от фишинга. Ключ можно хранить в Google Password Manager, 1Password, Связке ключей iCloud или Windows Hello — в зависимости от устройства и его настроек. Если подходящий способ недоступен, выберите логин и пароль.",
    "usernameLabel": "Логин",
    "passwordLabel": "Пароль аккаунта",
    "newPassword": "Новый пароль аккаунта",
    "usernameHelp": "Придумайте логин: 3–32 латинские буквы, цифры, точки, дефисы или подчёркивания. Первый символ — буква или цифра. Регистр букв не важен. Например: lena-work.",
    "passwordHelp": "От 15 до 128 символов. Сгенерируйте пароль или введите свой; сгенерированный пароль тоже можно отредактировать.",
    "showPassword": "Показать пароль",
    "hidePassword": "Скрыть пароль",
    "generatePassword": "Сгенерировать",
    "passwordSignIn": "Войти",
    "saveCredentialsHint": "Перед продолжением сохраните логин и пароль в менеджере паролей. Это пароль аккаунта TOLF; у VPN-подключений отдельные пароли.",
    "resetHelp": "Введите сохранённый логин, код восстановления и новый пароль. Прежние сеансы входа в аккаунт будут закрыты. VPN-профили и существующие Passkey сохранятся.",
    "passwordRecoverDescription": "Используйте код, сохранённый при регистрации с логином и паролем.",
    "resetPassword": "Задать новый пароль",
    "saveRecoveryDescription": "Сохраните код в надёжном месте. Он даёт доступ к аккаунту, поэтому никому его не передавайте. По почте мы его не отправляем.",
    "recoveryInstructions": "Если потеряете доступ, откройте TOLF → Войти → Восстановить аккаунт. Выберите свой способ входа и введите этот код; для восстановления пароля также укажите логин. После восстановления сохраните новый код: старый перестанет действовать. Если потерять и данные для входа, и код, восстановить аккаунт не получится.",
    "downloadCredentials": "Скачать данные для входа",
    "savedAcknowledgement": "Я сохранил данные для входа и код восстановления.",
    "savingAccount": "Создание аккаунта…",
    "signingIn": "Вход…",
    "savedRequired": "Сохраните данные для входа и код, затем отметьте это галочкой.",
    "invalid_username": "Используйте 3–32 латинские буквы, цифры, точки, дефисы или подчёркивания. Начните с буквы или цифры.",
    "invalid_password": "Длина пароля — от 15 до 128 символов.",
    "weak_password": "Выберите менее предсказуемый пароль или сгенерируйте его.",
    "username_taken": "Этот логин уже занят. Выберите другой.",
    "invalid_credentials": "Неверный логин или пароль.",
    "invalid_recovery": "Неверный логин или код восстановления, либо код уже заменён новым.",
    "too_many_attempts": "Слишком много попыток. Повторите через 15 минут.",
    "try_later": "Повторите через несколько секунд.",
    "invalid_origin": "Перезагрузите страницу входа TOLF и повторите попытку.",
    "passwordUnavailable": "Вход по паролю временно недоступен. Попробуйте позже.",
    "passwordSessionExpired": "Войдите снова с логином и паролем. Аккаунт уже создан.",
    "downloadNote": "Храните этот файл в тайне: он содержит данные доступа к аккаунту."
  },
  "lv": {
    "signInDescription": "Izvēlieties, kā pieteikties savā TOLF kontā.",
    "signupDescription": "Izvēlieties pieteikšanās veidu. E-pasts un tālruņa numurs nav nepieciešams.",
    "passwordMethod": "Lietotājvārds un parole",
    "passkeyAbout": "Passkey ir ērta pieteikšanās bez paroles ar aizsardzību pret pikšķerēšanu. Atslēgu var glabāt Google Password Manager, 1Password, iCloud Keychain vai Windows Hello atkarībā no ierīces un tās iestatījumiem. Ja piemērots veids nav pieejams, izvēlieties lietotājvārdu un paroli.",
    "usernameLabel": "Lietotājvārds",
    "passwordLabel": "Konta parole",
    "newPassword": "Jaunā konta parole",
    "usernameHelp": "Izvēlieties savu lietotājvārdu: 3–32 latīņu burti, cipari, punkti, defises vai pasvītrojumi. Sāciet ar burtu vai ciparu. Lielie un mazie burti netiek atšķirti. Piemēram: lena-work.",
    "passwordHelp": "15–128 rakstzīmes. Ģenerējiet paroli vai ievadiet savu; ģenerēto paroli arī var rediģēt.",
    "showPassword": "Rādīt paroli",
    "hidePassword": "Paslēpt paroli",
    "generatePassword": "Ģenerēt paroli",
    "passwordSignIn": "Pieteikties",
    "saveCredentialsHint": "Pirms turpināt, saglabājiet lietotājvārdu un paroli paroļu pārvaldniekā. Šī ir TOLF konta parole; VPN savienojumiem ir atsevišķas paroles.",
    "resetHelp": "Ievadiet saglabāto lietotājvārdu, atkopšanas kodu un jauno paroli. Iepriekšējās konta sesijas tiks slēgtas. VPN profili un esošās Passkey atslēgas saglabāsies.",
    "passwordRecoverDescription": "Izmantojiet kodu, ko saglabājāt, reģistrējoties ar lietotājvārdu un paroli.",
    "resetPassword": "Iestatīt jaunu paroli",
    "saveRecoveryDescription": "Saglabājiet kodu drošā vietā. Tas nodrošina piekļuvi kontam, tāpēc neizpaudiet to citiem. Mēs to nesūtām pa e-pastu.",
    "recoveryInstructions": "Ja zaudējat piekļuvi, atveriet TOLF → Pieteikties → Atjaunot kontu. Izvēlieties savu pieteikšanās veidu un ievadiet šo kodu; paroles atjaunošanai ievadiet arī lietotājvārdu. Pēc atjaunošanas saglabājiet jauno kodu: vecais vairs nedarbosies. Ja pazaudēsiet gan pieteikšanās datus, gan kodu, kontu nevarēs atjaunot.",
    "downloadCredentials": "Lejupielādēt piekļuves datus",
    "savedAcknowledgement": "Esmu saglabājis pieteikšanās datus un atkopšanas kodu.",
    "savingAccount": "Veido kontu…",
    "signingIn": "Piesakās…",
    "savedRequired": "Saglabājiet piekļuves datus un kodu, pēc tam atzīmējiet izvēles rūtiņu.",
    "invalid_username": "Izmantojiet 3–32 latīņu burtus, ciparus, punktus, defises vai pasvītrojumus. Sāciet ar burtu vai ciparu.",
    "invalid_password": "Parolei jābūt 15–128 rakstzīmes garai.",
    "weak_password": "Izvēlieties grūtāk uzminamu paroli vai ģenerējiet to.",
    "username_taken": "Šis lietotājvārds jau ir aizņemts. Izvēlieties citu.",
    "invalid_credentials": "Nepareizs lietotājvārds vai parole.",
    "invalid_recovery": "Nepareizs lietotājvārds vai atkopšanas kods, vai kods jau ir aizstāts.",
    "too_many_attempts": "Pārāk daudz mēģinājumu. Mēģiniet pēc 15 minūtēm.",
    "try_later": "Mēģiniet vēlreiz pēc dažām sekundēm.",
    "invalid_origin": "Pārlādējiet TOLF pieteikšanās lapu un mēģiniet vēlreiz.",
    "passwordUnavailable": "Pieteikšanās ar paroli īslaicīgi nav pieejama. Mēģiniet vēlāk.",
    "passwordSessionExpired": "Piesakieties vēlreiz ar lietotājvārdu un paroli. Konts jau ir izveidots.",
    "downloadNote": "Glabājiet šo failu privāti: tajā ir konta piekļuves dati."
  }
};
Object.keys(passwordCopy).forEach(lang => Object.assign(copy[lang], passwordCopy[lang]));

Object.assign(copy.en, {"saveRecoveryTitle":"Save your account details","saveRecoveryDescription":"Download a text file with your sign-in and recovery details. Keep it somewhere safe and do not share it.","downloadCredentials":"Download sign-in and recovery details","savedAcknowledgement":"I saved the file.","savedContinue":"Continue"});
Object.assign(copy.ru, {"saveRecoveryTitle":"Сохраните данные аккаунта","saveRecoveryDescription":"Скачайте текстовый файл с данными для входа и восстановления. Храните его в надёжном месте и никому не передавайте.","downloadCredentials":"Скачать данные для входа и восстановления","savedAcknowledgement":"Я сохранил файл.","savedContinue":"Продолжить"});
Object.assign(copy.lv, {"saveRecoveryTitle":"Saglabājiet konta datus","saveRecoveryDescription":"Lejupielādējiet teksta failu ar pieteikšanās un atkopšanas datiem. Glabājiet to drošā vietā un neizpaudiet citiem.","downloadCredentials":"Lejupielādēt pieteikšanās un atkopšanas datus","savedAcknowledgement":"Es saglabāju failu.","savedContinue":"Turpināt"});

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
const continueButton = document.getElementById("continueButton");
const passkeyName = document.getElementById("passkeyName");
const recoveryCode = document.getElementById("recoveryCode");
const newRecoveryCode = document.getElementById("newRecoveryCode");
const backHome = document.getElementById("backHome");

const url = new URL(window.location.href);
const requestedLang = url.searchParams.get("lang");
const requestedMode = url.searchParams.get("mode");
const next = ["vpn", "quick", "account"].includes(url.searchParams.get("next")) ? url.searchParams.get("next") : "home";

function storedLanguage() {
  try { return localStorage.getItem("tolf-language") || localStorage.getItem("tolfLanguage"); } catch { return null; }
}

let language = ["en", "ru", "lv"].includes(requestedLang)
  ? requestedLang
  : storedLanguage();

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
  const base = next === "account" ? "https://vpn.tolf.is/account/" : next === "quick" ? "https://vpn.tolf.is/quick/" : next === "vpn" ? "https://vpn.tolf.is/" : "https://tolf.is/";
  const target = new URL(base);
  target.searchParams.set("lang", language);
  target.searchParams.set("ui", "20260918-1");
  return target.toString();
}

function setLanguage(nextLanguage) {
  if (!["en", "ru", "lv"].includes(nextLanguage)) return;
  language = nextLanguage;
  document.documentElement.lang = language;
  try {
    localStorage.setItem("tolf-language", language);
    localStorage.setItem("tolfLanguage", language);
  } catch { /* Language switching also works when Safari blocks storage. */ }

  document.querySelectorAll("[data-i18n]").forEach(element => {
    element.textContent = text(element.dataset.i18n);
  });

  Object.entries(langButtons).forEach(([key, button]) => {
    button.classList.toggle("active", key === language);
    button.setAttribute("aria-pressed", key === language ? "true" : "false");
  });

  backHome.setAttribute("aria-label", text("backHome").replace(/^←\s*/, ""));
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

  if (mode === "signup") requestAnimationFrame(() => (authMethod === "password" ? document.getElementById("signupUsername") : passkeyName).focus());
  if (mode === "recover") requestAnimationFrame(() => recoveryCode.focus());
}

function setMessage(id, value = "", state = "") {
  const element = document.getElementById(id);
  element.textContent = value;
  element.className = `message${state ? ` ${state}` : ""}`;
}

function setBusy(value) {
  busy = value;
  document.querySelectorAll('.auth-card button, .auth-card input').forEach(element => { element.disabled = value; });
  continueButton.disabled = value || !credentialsSaved.checked;
}

async function apiRequest(path, options = {}) {
  const response = await fetch(API + path, {
    credentials: "include",
    cache: "no-store",
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
    if (savedCredentials) throw new Error(text("passwordSessionExpired"));
    setMessage(messageId, text("signingInAfterRegistration"));
    await startSignIn(messageId);
  }
  savedCredentials = null;
  newRecoveryCode.textContent = "";
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

    showRecovery(finish);
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
    showRecovery(finish);
  } catch (error) {
    setMessage("recoverMessage", error.message, "error");
  } finally {
    setBusy(false);
  }
});

continueButton.addEventListener("click", async () => {
  if (!credentialsSaved.checked) { setMessage("recoveryCodeMessage", text("savedRequired"), "error"); return; }
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

// No account passwords or recovery codes are stored in browser storage.
let authMethod = 'passkey';
let passwordReady = false;
let busy = false;
let savedCredentials = null;
const credentialsSaved = document.getElementById('credentialsSaved');
const savedUsername = document.getElementById('savedUsername');
function updateMethod() {
  document.querySelectorAll('[data-auth-method]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.authMethod === authMethod));
  });
  document.querySelectorAll('[data-for-method]').forEach(element => {
    element.classList.toggle('hidden', element.dataset.forMethod !== authMethod);
  });
  const description = document.querySelector('[data-i18n="recoverDescription"], [data-i18n="passwordRecoverDescription"]');
  description.dataset.i18n = authMethod === 'password' ? 'passwordRecoverDescription' : 'recoverDescription';
  description.textContent = text(description.dataset.i18n);
}
document.querySelectorAll('[data-auth-method]').forEach(button => {
  button.addEventListener('click', () => {
    if (busy || !passwordReady) return;
    authMethod = button.dataset.authMethod;
    updateMethod();
    ['signInMessage','signupMessage','recoverMessage'].forEach(id => setMessage(id));
  });
});
document.querySelectorAll('[data-toggle-password]').forEach(button => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.togglePassword);
    input.type = input.type === 'password' ? 'text' : 'password';
    button.dataset.i18n = input.type === 'password' ? 'showPassword' : 'hidePassword';
    button.textContent = text(button.dataset.i18n);
    button.setAttribute('aria-pressed', String(input.type === 'text'));
  });
});
document.querySelectorAll('[data-generate-password]').forEach(button => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.generatePassword);
    // 64-symbol alphabet, uniform selection, 120 bits from Web Crypto.
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
    input.value = Array.from(crypto.getRandomValues(new Uint8Array(20)), n => alphabet[n & 63]).join('');
    input.type = 'text';
    const toggle = document.querySelector('[data-toggle-password="'+input.id+'"]');
    toggle.dataset.i18n = 'hidePassword';
    toggle.textContent = text('hidePassword');
    toggle.setAttribute('aria-pressed', 'true');
    input.dispatchEvent(new Event('input', {bubbles:true}));
    input.focus();
  });
});
function showRecovery(finish, credentials = null) {
  savedCredentials = credentials;
  newRecoveryCode.textContent = finish.recoveryCode;
  credentialsSaved.checked = false;
  savedUsername.classList.toggle('hidden', !credentials);
  savedUsername.textContent = credentials ? text('usernameLabel')+': '+credentials.username : '';
  setMessage('recoveryCodeMessage');
  setMode('recovery', false);
  continueButton.disabled = true;
}
credentialsSaved.addEventListener('change', () => { continueButton.disabled = busy || !credentialsSaved.checked; });
window.addEventListener('beforeunload', event => {
  if (currentMode === 'recovery' && !credentialsSaved.checked) { event.preventDefault(); event.returnValue = ''; }
});
function credentialText() {
  const parts = ['TOLF — https://vpn.tolf.is/auth/', text('downloadNote'), ''];
  if (savedCredentials) parts.push(text('usernameLabel')+': '+savedCredentials.username, text('passwordLabel')+': '+savedCredentials.password, '');
  parts.push(text('recoveryCode')+': '+newRecoveryCode.textContent, '', text('recoveryInstructions'));
  return parts.join('\n')+'\n';
}
document.getElementById('downloadCredentialsButton').addEventListener('click', () => {
  const address = URL.createObjectURL(new Blob([credentialText()], {type:'text/plain;charset=utf-8'}));
  const link = document.createElement('a'); link.href = address; link.download = 'TOLF-account-recovery.txt';
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(address), 1000);
});
for (const [formId, prefix, action, message] of [
  ['passwordLoginForm','login','login','signInMessage'],
  ['passwordSignupForm','signup','register','signupMessage'],
  ['passwordResetForm','reset','recover','recoverMessage']
]) {
  document.getElementById(formId).addEventListener('submit', async event => {
    event.preventDefault();
    if (busy) return;
    if (!passwordReady) { setMessage(message, text('passwordUnavailable'), 'error'); return; }
    const input = document.getElementById(prefix+'Password');
    const nameInput = document.getElementById(prefix+'Username');
    const name = nameInput.value.toLowerCase();
    const value = input.value;
    const payload = {username:name, password:value};
    if (action === 'recover') {
      payload.recoveryCode = recoveryCode.value.trim().toUpperCase();
      if (!payload.recoveryCode) { setMessage(message,text('recoveryRequired'),'error'); recoveryCode.focus(); return; }
    }
    setBusy(true);
    setMessage(message, text(action === 'register' ? 'savingAccount' : action === 'login' ? 'signingIn' : 'checkingRecovery'));
    try {
      const result = await apiRequest('/password/'+action, {method:'POST',body:JSON.stringify(payload)});
      if (action === 'login') { input.value = ''; window.location.assign(destination()); }
      else {
        if (!result?.recoveryCode) throw new Error(text('recoveryCodeMissing'));
        showRecovery(result, {username:result.username || name, password:value});
        input.value = ''; recoveryCode.value = '';
      }
    } catch (error) { setMessage(message, text(error.message), 'error'); }
    finally { setBusy(false); }
  });
}
async function checkPasswordCapability() {
  try {
    const result = await apiRequest('/password/capabilities', {method:'GET', signal:AbortSignal.timeout(8000)});
    passwordReady = result?.version === 1;
  } catch { passwordReady = false; }
  document.querySelectorAll('[data-method-selector]').forEach(element => element.classList.toggle('hidden', !passwordReady));
}

setLanguage(language);
setMode(currentMode, false);
checkPasswordCapability();

alreadyAuthenticated().then(authenticated => {
  if (authenticated && currentMode !== "recover") window.location.replace(destination());
});

