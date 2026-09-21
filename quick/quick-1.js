(() => {
'use strict';
const $ = id => document.getElementById(id);
const API = 'https://api.tolf.is';
const nativePlatform = /Android/i.test(navigator.userAgent) ? 'android' : /Windows NT/i.test(navigator.userAgent) ? 'windows' : 'ios';
const get = (key, fallback) => { try { return sessionStorage.getItem(key) || fallback; } catch { return fallback; } };
const put = (key, value) => { try { if(value) sessionStorage.setItem(key, value); else sessionStorage.removeItem(key); } catch {} };
let lang; try { lang = localStorage.getItem('tolfLanguage'); } catch {}
if (!QUICK_TEXT[lang]) lang = /^ru/i.test(navigator.language) ? 'ru' : /^lv/i.test(navigator.language) ? 'lv' : 'en';
const t = key => QUICK_TEXT[lang][key] || key;
const accountText = {en:['Create account','Sign in','Choose Passkey or username and password. No email address is required.'],ru:['Создать аккаунт','Войти','Выберите Passkey или логин и пароль. Электронная почта не нужна.'],lv:['Izveidot kontu','Pieteikties','Izvēlieties Passkey vai lietotājvārdu un paroli. E-pasts nav nepieciešams.']};
function accountAuth(mode) { persist(); window.location.assign('/auth/?mode='+mode+'&next=quick&lang='+lang); }
let busy = false, authenticated = false, ready = false, locked = false, choicesOpened = false, profile = '', messageKey = '', failed = false;
let server = ['riga','moscow'].includes(get('quickServer')) ? get('quickServer') : 'riga';
let platform = ['ios','android','windows'].includes(get('quickPlatform')) ? get('quickPlatform') : nativePlatform;
let manual = get('quickManual') === 'yes';
let uncertain = get('quickRegistration') === 'pending';
let loadNumber = 0;
const suggestedPasskeyName = /iPad/i.test(navigator.userAgent) || (navigator.platform==='MacIntel' && navigator.maxTouchPoints>1) ? 'iPad' : nativePlatform==='ios'?'iPhone':nativePlatform==='windows'?'Windows':'Android';
$('passkeyName').value = suggestedPasskeyName;
function message(key, error = false) { messageKey = key; failed = error; render(); }
function persist() { put('quickServer', server); put('quickPlatform', platform); }
function render() {
 document.documentElement.lang = lang;
 document.querySelectorAll('[data-text]').forEach(el => el.textContent = t(el.dataset.text));
 $('passkeyHelp').textContent = accountText[lang][2];
 $('windowsPrep').hidden = true;
 $('passkeyNameField').hidden = true;
 $('register').textContent = accountText[lang][0];
 $('login').textContent = accountText[lang][1];
 document.querySelectorAll('[data-lang]').forEach(el => { el.setAttribute('aria-pressed', String(el.dataset.lang === lang)); el.disabled = busy; });
 $('deviceSummary').textContent = platform === 'ios' ? 'iPhone / iPad' : platform === 'android' ? 'Android' : 'Windows';
 $('platform').value = platform; $('server').value = server;
 $('message').textContent = t(messageKey); $('message').className = failed ? 'error' : '';
 for (const id of ['change','platform','server']) $(id).disabled = busy || locked;
 $('change').hidden = locked || choicesOpened;
 for (const id of ['register','login','saved','prepare','copyCode','copyLink','copyChromeSettings','share','retry']) $(id).disabled = busy;
 $('register').hidden = uncertain;
 $('login').hidden = false;
 if(profile) renderDelivery();
}
function panels(name) {
 for (const id of ['auth','recovery','preparePanel','delivery']) $(id).hidden = id !== name;
 $('retry').hidden = true;
 render();
}
async function api(path, options={}) {
 const response = await fetch(API+path,{credentials:'include',cache:'no-store',...options,
 headers:{'Content-Type':'application/json',...(options.headers||{})}});
 let data;
 try { data = await response.json(); } catch { data = {}; }
 if(!response.ok) { const e = new Error(data.detail || 'Request failed'); e.status = response.status; throw e; }
 return data;
}
function errorMessage(error) {
 if(error && error.messageKey)return error.messageKey;
 if(error && error.name === 'NotAllowedError')return nativePlatform === 'windows' ? 'passkeyWindowsNotAllowed' : 'passkeyNotAllowed';
 if(error && (error.name === 'NotSupportedError' || error.name === 'SecurityError'))return 'passkeyUnavailable';
 if(error && error.name === 'AbortError')return 'passkeyCancelled';
 return 'failed';
}
async function action(fn) {
 if(busy) return;
 busy=true; render();
 try { await fn(); }
 catch(e) {
  if(e.status===401) { authenticated=false; panels('auth'); message('loginRequired',true); }
  else message(errorMessage(e),true);
 }
 finally { busy=false; render(); }
}
async function loadAccount() {
 const me = await api('/me');
 if(!me.authenticated) throw Object.assign(new Error('Sign in required'),{status:401});
 authenticated=true; uncertain=false; put('quickRegistration','');
 const state = await api('/quick-setup/status');
 if(state.setup) {
  platform=state.setup.platform; server=state.setup.server; locked=true; manual=true; persist();
  $('choices').hidden=true;
  message('savedSelection');
 }
 panels('preparePanel');
}
async function initialize() {
 const number=++loadNumber;
 busy=true; panels(''); message('loading');
 try {
  const capabilities=await api('/quick-setup/capabilities');
  if(capabilities.version!==1) throw new Error('Unavailable');
  ready=true;
  if(!manual) server='riga';
  // IP-based recommendation only. Latency does not change this selection.
  try {
   const r=await fetch(API+'/entry-point-recommendation',{credentials:'omit',cache:'no-store',signal:AbortSignal.timeout(4000)});
   if(r.ok) { const data=await r.json(); if(!manual && number===loadNumber) server=data.entryPoint==='moscow'?'moscow':'riga'; }
  } catch { /* Riga is the fallback; a user's saved choice is preserved. */ }
  if(number!==loadNumber)return;
  persist();
  try { await loadAccount(); if(!locked) message(''); }
  catch(e) { if(e.status!==401)throw e; panels('auth'); message(uncertain?'uncertain':'',uncertain); }
 } catch { ready=false; message('unavailable',true); $('retry').hidden=false; }
 finally { busy=false;render(); }
}
$('change').onclick=()=>{choicesOpened=true;$('choices').hidden=false;render();};
$('platform').onchange=()=>{platform=$('platform').value;persist();render();};
$('server').onchange=()=>{server=$('server').value;manual=true;put('quickManual','yes');persist();render();};
document.querySelectorAll('[data-lang]').forEach(el=>el.onclick=()=>{lang=el.dataset.lang;try{localStorage.setItem('tolfLanguage',lang);}catch{}render();});
$('retry').onclick=()=>initialize();
$('register').onclick=()=>accountAuth('signup');
$('login').onclick=()=>accountAuth('signin');
async function prepare() {
 if(!authenticated)return;
 locked=true;$('choices').hidden=true; message('busy');
 const data=await api('/quick-setup/prepare',{method:'POST',body:JSON.stringify({platform,server,language:lang})});
 const url=new URL(data.profileUrl);
 const allowed=['api.tolf.is','config.tolf.is','install-ru.tolf.is'];
 if(url.protocol!=='https:' || !allowed.includes(url.hostname) || url.username || url.password)throw new Error('Invalid profile link');
 profile=url.href;panels('delivery');message('');
}
$('saved').onclick=()=>action(async()=>{$('code').value='';panels('preparePanel');await prepare();});
$('prepare').onclick=()=>action(prepare);
function renderDelivery(){
 const other=platform!==nativePlatform;
 $('deliveryHelp').textContent=t(other?'otherHelp':platform+'Help');
 $('downloadHelp').textContent=other?'':t(platform+'Steps');
 $('download').hidden=other;
 let url=new URL(profile);
 if(platform!=='android' && !/\.(mobileconfig|sswan)$/i.test(url.pathname) && !url.pathname.endsWith('/download'))url.pathname=url.pathname.replace(/\/$/,'')+'/download';
 $('download').href=url.href;$('download').textContent=t(platform+'Download');
 $('android').hidden=other || platform!=='android';
 $('sharing').hidden=!other;$('profileLink').value=profile;
 $('share').hidden=typeof navigator.share!=='function';
}
$('download').onclick=()=>message('started');
async function copy(id){
 const input=$(id);input.focus();input.select();
 try {await navigator.clipboard.writeText(input.value);message('copied');}
 catch { /* Keep the actual text selected for manual copying, no false success. */ }
}
$('copyCode').onclick=()=>copy('code');$('copyLink').onclick=()=>copy('profileLink');
$('copyChromeSettings').onclick=()=>copy('chromeSettings');
$('share').onclick=async()=>{try{await navigator.share({title:'TOLF VPN',url:profile});}catch(e){if(e.name!=='AbortError')message('failed',true);}};
window.addEventListener('pageshow',e=>{if(e.persisted){profile='';$('code').value='';initialize();}});
render();initialize();
})();

