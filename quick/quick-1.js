(() => {
'use strict';
const $ = id => document.getElementById(id);
const API = 'https://api.tolf.is';
const nativePlatform = /Android/i.test(navigator.userAgent) ? 'android' : /Windows NT/i.test(navigator.userAgent) ? 'windows' : /iPhone|iPad|iPod/i.test(navigator.userAgent) || (navigator.platform==='MacIntel' && navigator.maxTouchPoints>1) ? 'ios' : null;
const get = (key, fallback) => { try { return sessionStorage.getItem(key) || fallback; } catch { return fallback; } };
const put = (key, value) => { try { if(value) sessionStorage.setItem(key, value); else sessionStorage.removeItem(key); } catch {} };
const requestedProtocol=new URL(location.href).searchParams.get('protocol');
const protocol=requestedProtocol==='anyconnect' || (!requestedProtocol&&get('quickProtocol')==='anyconnect')?'anyconnect':'ikev2';
let ocGrant=null,ocPoint=null,ocDevice=null,ocConfirmed=false,ocImported=false,accountId=null,ocExpiryTimer=null;
let lang; try { lang = localStorage.getItem('tolfLanguage'); } catch {}
if (!QUICK_TEXT[lang]) lang = /^ru/i.test(navigator.language) ? 'ru' : /^lv/i.test(navigator.language) ? 'lv' : 'en';
const t = key => QUICK_TEXT[lang][key] || key;
const accountText = {en:['Create account','Sign in','Choose Passkey or username and password. No email address is required.'],ru:['Создать аккаунт','Войти','Выберите Passkey или логин и пароль. Электронная почта не нужна.'],lv:['Izveidot kontu','Pieteikties','Izvēlieties Passkey vai lietotājvārdu un paroli. E-pasts nav nepieciešams.']};
function accountAuth(mode) { persist(); window.location.assign('/auth/?mode='+mode+'&next=quick&lang='+lang); }
let busy = false, authenticated = false, ready = false, locked = false, choicesOpened = false, profile = '', messageKey = '', failed = false;
let server = null;
let platform = nativePlatform;

let uncertain = get('quickRegistration') === 'pending';
let loadNumber = 0;
const suggestedPasskeyName = /iPad/i.test(navigator.userAgent) || (navigator.platform==='MacIntel' && navigator.maxTouchPoints>1) ? 'iPad' : nativePlatform==='ios'?'iPhone':nativePlatform==='windows'?'Windows':'Android';
$('passkeyName').value = suggestedPasskeyName;
function message(key, error = false) { messageKey = key; failed = error; render(); }
function persist() { put('quickServer', server); put('quickPlatform', platform);put('quickProtocol',protocol); }
function render() {
 document.documentElement.lang = lang;
 $('quickProtocolName').textContent=protocol==='anyconnect'?'AnyConnect':'IKEv2';
 const back=document.getElementById('backHome');
 if(back){back.href='/?lang='+lang;back.setAttribute('aria-label',({ru:'Назад в Мой VPN',en:'Back to My VPN',lv:'Atpakaļ uz Mans VPN'})[lang]);}
 document.querySelectorAll('[data-text]').forEach(el => el.textContent = t(el.dataset.text));
 $('passkeyHelp').textContent = accountText[lang][2];
 $('windowsPrep').hidden = true;
 $('passkeyNameField').hidden = true;
 $('register').textContent = accountText[lang][0];
 $('login').textContent = accountText[lang][1];
 document.querySelectorAll('[data-lang]').forEach(el => { el.setAttribute('aria-pressed', String(el.dataset.lang === lang)); el.disabled = busy; });
 $('deviceSummary').textContent = platform === 'ios' ? 'iPhone / iPad' : platform === 'android' ? 'Android' : platform==='windows'?'Windows':t('unsupportedDevice');
 $('platform').value = platform||''; $('server').textContent = server?t(server):'—';
 $('message').textContent = t(messageKey); $('message').className = failed ? 'error' : '';
 for (const id of ['change','platform','server']) $(id).disabled = busy || locked;
 $('change').hidden = true; $('choices').hidden = true;
 for (const id of ['register','login','saved','prepare','copyCode','copyLink','copyChromeSettings','share','retry']) $(id).disabled = busy || (!ready && id==='prepare');
 $('register').hidden = uncertain;
 $('login').hidden = false;
 if(profile) renderDelivery();
 if(ocDevice)renderOcDelivery();

}
function panels(name) {
 for (const id of ['auth','recovery','preparePanel','delivery','ocDelivery']) $(id).hidden = id !== name;
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
 accountId=me.userId;authenticated=true; uncertain=false; put('quickRegistration','');
 panels('preparePanel');
}
async function initialize() {
 const number=++loadNumber;
 busy=true; panels(''); message('loading');
 try {
  const capabilities=await api('/quick-setup/capabilities');
  if(capabilities.version!==1) throw new Error('Unavailable');
  if(!nativePlatform){ready=false;message('unsupportedDevice',true);return;}
  const r=await fetch(API+'/entry-point-recommendation',{credentials:'omit',cache:'no-store',signal:AbortSignal.timeout(6000)});
  if(!r.ok)throw new Error('Recommendation unavailable');
  const recommendation=await r.json();
  if(!['riga','moscow'].includes(recommendation.entryPoint))throw new Error('Invalid recommendation');
  server=recommendation.entryPoint;platform=nativePlatform;ready=true;
  if(protocol==='anyconnect'){
   const oc=await api('/oc/access/capabilities');
   ocPoint=oc.ingresses?.find(p=>p.id===server);
   if(oc.issuance!==true||!ocPoint||!['oc.tolf.is:4443','oc-riga.tolf.is:443'].includes(ocPoint.host))throw new Error('AnyConnect node unavailable');
  }
  if(number!==loadNumber)return;
  persist();
  try { await loadAccount(); if(!locked) message(''); }
  catch(e) { if(e.status!==401)throw e; panels('auth'); message(uncertain?'uncertain':'',uncertain); }
 } catch { ready=false; message('unavailable',true); $('retry').hidden=false; }
 finally { busy=false;render(); }
}
document.querySelectorAll('[data-lang]').forEach(el=>el.onclick=()=>{lang=el.dataset.lang;try{localStorage.setItem('tolfLanguage',lang);}catch{}render();});
$('retry').onclick=()=>initialize();
$('register').onclick=()=>accountAuth('signup');
$('login').onclick=()=>accountAuth('signin');
async function prepare() {
 if(!authenticated||!ready||!nativePlatform)return;
 locked=true;$('choices').hidden=true; message('busy');
 if(protocol==='anyconnect'){await prepareOc();return;}
 const data=await api('/quick-setup/prepare',{method:'POST',body:JSON.stringify({platform:nativePlatform,server,language:lang,currentDevice:true})});
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
window.addEventListener('pagehide',()=>{clearTimeout(ocExpiryTimer);ocGrant=null;$('ocPassword').value='';$('ocImport').removeAttribute('href');});
window.addEventListener('pageshow',e=>{if(e.persisted){profile='';ocGrant=null;ocDevice=null;ocConfirmed=false;ocImported=false;$('code').value='';initialize();}});

function ocKey(suffix){return 'quickOc:'+accountId+':'+nativePlatform+':'+suffix;}
function validateOcGrant(grant){
 const point=grant.connections?.find(p=>p.id===server);
 if(!point||typeof grant.password!=='string'||!Number.isFinite(Date.parse(grant.expiresAt))||Date.parse(grant.expiresAt)<=Date.now())throw Error('Invalid certificate grant');
 const certificate=new URL(grant.certificateUrl);
 if(certificate.protocol!=='https:'||certificate.hostname!=='api.tolf.is'||certificate.username||certificate.password||!certificate.pathname.startsWith('/oc/access/import/'))throw Error('Invalid certificate URL');
 const connect=new URL(point.connectionUri),importLink=new URL(grant.importUri);
 if(connect.protocol!=='anyconnect:'||connect.hostname!=='create'||connect.searchParams.get('host')!==point.host||connect.searchParams.get('certcommonname')!==grant.username)throw Error('Invalid connection');
 if(importLink.protocol!=='anyconnect:'||importLink.hostname!=='import'||importLink.searchParams.get('uri')!==grant.certificateUrl)throw Error('Invalid import');
 return point;
}
async function prepareOc(){
 if(!accountId)throw Error('Account unavailable');
 let deviceId=get(ocKey('device'));
 if(deviceId){
  const list=await api('/oc/access/devices');
  ocDevice=list.devices?.find(d=>d.id===deviceId&&d.state==='active'&&Date.parse(d.expires_at)>Date.now());
  if(!ocDevice){
   deviceId=null;put(ocKey('device'),'');put(ocKey('request'),'');
  }
 }
 if(!deviceId){
  let requestId=get(ocKey('request'));
  if(!requestId){requestId=crypto.randomUUID();put(ocKey('request'),requestId);}
  const result=await api('/oc/access/devices',{method:'POST',body:JSON.stringify({requestId,label:suggestedPasskeyName})});
  if(result.device?.state!=='active'||!result.device?.id)throw Error('Device not ready');
  ocDevice=result.device;deviceId=ocDevice.id;put(ocKey('device'),deviceId);
 }
 if(!ocDevice.username)throw Error('Device identity unavailable');
 ocConfirmed=false;ocImported=false;ocGrant=null;
 panels('ocDelivery');message('');
}
async function prepareOcImport(){
 if(!ocDevice||!ocConfirmed)return;
 ocImported=false;ocGrant=null;
 const deviceId=ocDevice.id;
 const grant=await api('/oc/access/devices/'+encodeURIComponent(deviceId)+'/import',{method:'POST',body:'{}'});
 if(grant.deviceId!==deviceId)throw Error('Wrong certificate');
 const point=validateOcGrant(grant);
 if(point.host!==ocPoint.host||grant.username!==ocDevice.username)throw Error('Wrong connection identity');
 ocGrant=grant;
 clearTimeout(ocExpiryTimer);ocExpiryTimer=setTimeout(()=>{if(ocGrant===grant)render();},Math.max(0,Date.parse(grant.expiresAt)-Date.now()));
 panels('ocDelivery');message('');
}
function renderOcDelivery(){
 const mobile=nativePlatform!=='windows',valid=ocGrant&&Date.parse(ocGrant.expiresAt)>Date.now()&&ocConfirmed&&!ocImported;
 $('ocApp').href=nativePlatform==='ios'?'https://apps.apple.com/app/id1135064690':nativePlatform==='android'?'https://play.google.com/store/apps/details?id=com.cisco.anyconnect.vpn.android.avf':'https://www.cisco.com/c/en/us/support/security/secure-client-5/model.html';
 const prefix=server==='riga'?'TOLF Рига ':'TOLF Москва ';
 const name=ocDevice.connectionNames?.[server]||Array.from(prefix+ocDevice.label).slice(0,24).join('').trimEnd();
 $('ocConnection').href='anyconnect://create/?'+new URLSearchParams({name,host:ocPoint.host,usecert:'true',certcommonname:ocDevice.username,netroam:'true'});
 $('ocServer').textContent=t(server)+': '+ocPoint.host;
 $('ocConnection').hidden=!mobile;
 $('ocConnectionActions').hidden=ocConfirmed;$('ocConnectionCompleted').hidden=!ocConfirmed;
 for(const id of ['ocConfirmConnection','ocAgain'])$(id).disabled=busy;
 $('ocRenew').disabled=busy||!ocConfirmed;
 $('ocAlreadyImported').disabled=busy||!ocConfirmed;
 $('ocAlreadyImported').hidden=ocImported;
 $('ocCertificateDone').hidden=!ocImported;
 $('ocCertificateHint').textContent=t(!ocConfirmed?'ocBlocked':ocGrant&&!valid?'ocExpired':'ocCertificateHelp');
 $('ocGrantPanel').hidden=!valid;
 if(valid)$('ocImport').href=ocGrant.importUri;else $('ocImport').removeAttribute('href');
 $('ocImport').hidden=!mobile||!valid;
 $('ocControl').hidden=!mobile;$('ocWindowsConnection').hidden=mobile;$('ocWindowsCertificate').hidden=mobile||ocImported;
 $('ocPassword').value=valid?ocGrant.password:'';
 $('ocCopyPassword').setAttribute('aria-label',t('ocCopyPassword'));
 $('ocCopyPassword').title=t('ocCopyPassword');
 $('ocCopyPassword').disabled=busy||!valid;$('ocDownload').disabled=busy||!valid;
}
$('ocConfirmConnection').onclick=()=>{if(busy||!ocDevice)return;ocConfirmed=true;message('');};
$('ocAgain').onclick=()=>{if(busy)return;ocConfirmed=false;ocImported=false;ocGrant=null;clearTimeout(ocExpiryTimer);message('');};
$('ocAlreadyImported').onclick=()=>{if(busy||!ocConfirmed)return;ocImported=true;ocGrant=null;clearTimeout(ocExpiryTimer);message('');};
$('ocConnection').onclick=event=>{if(busy||!ocDevice)event.preventDefault();};

$('ocCopyPassword').onclick=()=>action(async()=>{if(!ocGrant||Date.parse(ocGrant.expiresAt)<=Date.now())throw Error('Expired');await navigator.clipboard.writeText(ocGrant.password);message('copied');});
$('ocImport').onclick=event=>{if(!ocGrant||Date.parse(ocGrant.expiresAt)<=Date.now()){event.preventDefault();message('ocExpired',true);}};
$('ocRenew').onclick=()=>action(prepareOcImport);
$('ocDownload').onclick=()=>action(async()=>{
 if(!ocGrant||Date.parse(ocGrant.expiresAt)<=Date.now())throw Error('Expired');
 const response=await fetch(ocGrant.certificateUrl,{credentials:'omit',cache:'no-store',signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw Error('Download failed');
 const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');
 a.href=url;a.download='TOLF-AnyConnect.p12';document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);message('started');
});

render();initialize();
})();

