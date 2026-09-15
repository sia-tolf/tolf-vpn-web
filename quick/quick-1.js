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
 $('passkeyHelp').textContent = t(nativePlatform === 'windows' ? 'passkeyWindows' : 'passkey');
 $('windowsPrep').hidden = nativePlatform !== 'windows' || uncertain;
 $('register').textContent = t(nativePlatform === 'windows' ? 'createWindows' : 'create');
 document.querySelectorAll('[data-lang]').forEach(el => { el.setAttribute('aria-pressed', String(el.dataset.lang === lang)); el.disabled = busy; });
 $('deviceSummary').textContent = platform === 'ios' ? 'iPhone / iPad' : platform === 'android' ? 'Android' : 'Windows';
 $('serverSummary').textContent = t(server);
 $('platform').value = platform; $('server').value = server;
 $('message').textContent = t(messageKey); $('message').className = failed ? 'error' : '';
 for (const id of ['change','platform','server']) $(id).disabled = busy || locked;
 $('change').hidden = locked || choicesOpened;
 for (const id of ['register','login','saved','prepare','copyCode','copyLink','copyChromeSettings','share','retry']) $(id).disabled = busy;
 $('register').hidden = uncertain;
 $('login').hidden = !uncertain && messageKey !== 'loginRequired';
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
$('register').onclick=()=>action(async()=>{
 if(!ready || uncertain)return;
 const passkeyName=$('passkeyName').value.trim();
 if(!passkeyName){$('passkeyName').focus();message('passkeyNameRequired',true);return;}
 if(!window.PublicKeyCredential || !navigator.credentials || typeof navigator.credentials.create !== 'function')throw Object.assign(new Error('Passkey unavailable'),{messageKey:'passkeyUnavailable'});
 message('waiting');persist();
 const begin=await api('/passkey/register/begin',{method:'POST',body:JSON.stringify({passkeyName})});
 const credential=await navigator.credentials.create({publicKey:prepareRegistrationOptions(begin.options)});
 if(!credential)throw new Error('No Passkey');
 // Once a finish request is sent, do not create a second account after a lost response.
 uncertain=true;put('quickRegistration','pending');
 let finish;
 try { finish=await api('/passkey/register/finish',{method:'POST',body:JSON.stringify({challengeId:begin.challengeId,credential:serializeCredential(credential)})}); }
 catch { panels('auth');message('uncertain',true);return; }
 if(!finish.recoveryCode){panels('auth');message('uncertain',true);return;}
 authenticated=true; uncertain=false;put('quickRegistration','');
 $('code').value=finish.recoveryCode;
 panels('recovery');message('');
});
$('login').onclick=()=>action(async()=>{
 message('waiting');
 const begin=await api('/passkey/login/begin',{method:'POST',body:'{}'});
 const credential=await navigator.credentials.get({publicKey:prepareAuthenticationOptions(begin.options)});
 if(!credential)throw new Error('No Passkey');
 await api('/passkey/login/finish',{method:'POST',body:JSON.stringify({challengeId:begin.challengeId,credential:serializeCredential(credential)})});
 await loadAccount();if(!locked)message('');
});
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
