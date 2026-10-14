(() => {
'use strict';
const $ = id => document.getElementById(id);
const API = 'https://api.tolf.is';
const nativePlatform = /Android/i.test(navigator.userAgent) ? 'android' : /Windows NT/i.test(navigator.userAgent) ? 'windows' : /iPhone|iPad|iPod/i.test(navigator.userAgent) || (navigator.platform==='MacIntel' && navigator.maxTouchPoints>1) ? 'ios' : null;
const get = (key, fallback) => { try { return sessionStorage.getItem(key) || fallback; } catch { return fallback; } };
const put = (key, value) => { try { if(value) sessionStorage.setItem(key, value); else sessionStorage.removeItem(key); } catch {} };
const requestedPlatform=new URL(location.href).searchParams.get('platform');
const windowsQuickBlocked=requestedPlatform==='windows'&&nativePlatform!=='windows';
const requestedProtocol=new URL(location.href).searchParams.get('protocol');
const protocol=requestedProtocol==='anyconnect' || (!requestedProtocol&&get('quickProtocol')==='anyconnect')?'anyconnect':'ikev2';
const requestedIngress=new URL(location.href).searchParams.get('ingress') || get('quickIngress', null);
const OC_HOSTS={riga:'oc-riga.tolf.is:443',moscow:'oc.tolf.is:4443',us:'oc-us.tolf.is:4443'};
let ocGrant=null,ocPoint=null,ocDevice=null,ocConfirmed=false,ocImported=false,accountId=null,ocExpiryTimer=null;
let lang; try { lang = localStorage.getItem('tolfLanguage'); } catch {}
if (!QUICK_TEXT[lang]) lang = /^ru/i.test(navigator.language) ? 'ru' : /^lv/i.test(navigator.language) ? 'lv' : 'en';
for(const [language,text] of Object.entries({
 ru:'На компьютере Windows откройте vpn.tolf.is, выберите Windows, нужный протокол и «Быстрая настройка». Настройки устанавливаются на этом компьютере.',
 en:'Open vpn.tolf.is on your Windows computer, select Windows, the desired protocol and “Quick setup”. The settings are installed on that computer.',
 lv:'Windows datorā atveriet vpn.tolf.is, atlasiet Windows, vajadzīgo protokolu un “Ātrā iestatīšana”. Iestatījumi tiek instalēti šajā datorā.'
}))QUICK_TEXT[language].windowsQuickOnly=text;
for(const [language,city] of Object.entries({ru:'Нью-Йорк',en:'New York',lv:'Ņujorka'}))QUICK_TEXT[language].us=city;
for(const [language,messages] of Object.entries({
 ru:{ocGrantInvalid:'Не удалось проверить ответ с сертификатом. Код проверки:',ocDownloadFailed:'Не удалось скачать сертификат. Нажмите «Получить сертификат» и повторите скачивание.'},
 en:{ocGrantInvalid:'The certificate response could not be verified. Check code:',ocDownloadFailed:'The certificate download failed. Get a new certificate and download it again.'},
 lv:{ocGrantInvalid:'Neizdevās pārbaudīt sertifikāta atbildi. Pārbaudes kods:',ocDownloadFailed:'Neizdevās lejupielādēt sertifikātu. Iegūstiet jaunu sertifikātu un mēģiniet vēlreiz.'}
}))Object.assign(QUICK_TEXT[language],messages);
const t = key => QUICK_TEXT[lang][key] || key;
const accountText = {en:['Create account','Sign in','Choose Passkey or username and password. No email address is required.'],ru:['Создать аккаунт','Войти','Выберите Passkey или логин и пароль. Электронная почта не нужна.'],lv:['Izveidot kontu','Pieteikties','Izvēlieties Passkey vai lietotājvārdu un paroli. E-pasts nav nepieciešams.']};
const OC_WINDOWS_TEXT={
 ru:{copy:'Копировать',start:'Откройте OpenConnect GUI. Нажмите шестерёнку → New profile (advanced).',fields:'Скопируйте значения в одноимённые поля:',defaults:'VPN protocol: Cisco AnyConnect or OpenConnect.\nUsername, Groupname, CA Certificate, User Key — оставьте пустыми. Остальные параметры оставьте без изменений.\nНажмите Save, затем здесь — «Соединение добавлено».',certificate:'1. Нажмите «Получить сертификат», скопируйте пароль и скачайте файл .p12.\n2. В OpenConnect GUI выберите профиль → шестерёнка → Edit selected profile.\n3. Откройте Local Certificate. Нажмите … у User Certificate и выберите скачанный .p12. Поле User Key оставьте пустым.\n4. Введите пароль сертификата, когда программа его запросит. Нажмите Save.',enable:'В OpenConnect GUI выберите профиль и нажмите Connect. Если появится запрос пароля сертификата, вставьте пароль с этой страницы.',help:'Скачайте .p12 и выберите его в Local Certificate → User Certificate.'},
 en:{copy:'Copy',start:'Open OpenConnect GUI. Select the gear → New profile (advanced).',fields:'Copy these values into the matching fields:',defaults:'VPN protocol: Cisco AnyConnect or OpenConnect.\nLeave Username, Groupname, CA Certificate and User Key empty. Keep the other settings unchanged.\nSelect Save, then “Connection added” here.',certificate:'1. Get the certificate, copy its password and download the .p12 file.\n2. In OpenConnect GUI select the profile → gear → Edit selected profile.\n3. Open Local Certificate. Select … beside User Certificate and choose the downloaded .p12. Leave User Key empty.\n4. Enter the certificate password when prompted. Select Save.',enable:'Select the profile in OpenConnect GUI and select Connect. If prompted for the certificate password, paste the password from this page.',help:'Download the .p12 and select it under Local Certificate → User Certificate.'},
 lv:{copy:'Kopēt',start:'Atveriet OpenConnect GUI. Izvēlieties zobratu → New profile (advanced).',fields:'Iekopējiet vērtības atbilstošajos laukos:',defaults:'VPN protocol: Cisco AnyConnect or OpenConnect.\nAtstājiet Username, Groupname, CA Certificate un User Key tukšus. Pārējos iestatījumus nemainiet.\nNospiediet Save, tad šeit — “Savienojums pievienots”.',certificate:'1. Iegūstiet sertifikātu, nokopējiet paroli un lejupielādējiet .p12 failu.\n2. OpenConnect GUI izvēlieties profilu → zobratu → Edit selected profile.\n3. Atveriet Local Certificate. Nospiediet … pie User Certificate un izvēlieties lejupielādēto .p12. Atstājiet User Key tukšu.\n4. Ievadiet sertifikāta paroli, kad lietotne to pieprasa. Nospiediet Save.',enable:'OpenConnect GUI izvēlieties profilu un nospiediet Connect. Ja tiek pieprasīta sertifikāta parole, ielīmējiet paroli no šīs lapas.',help:'Lejupielādējiet .p12 un izvēlieties to sadaļā Local Certificate → User Certificate.'}
};
function accountAuth(mode) { persist(); window.location.assign('/auth/?mode='+mode+'&next=quick&lang='+lang); }
let busy = false, authenticated = false, ready = false, locked = false, choicesOpened = false, profile = '', messageKey = '', failed = false;
let server = null;
let iosButtons = get('quickIosButtons') === 'true';
let platform = windowsQuickBlocked?'windows':nativePlatform;

const clientHandoff=(()=>{
 const raw=get('quickClientHandoff',null);
 put('quickClientHandoff','');
 try{
  const value=JSON.parse(raw),age=Date.now()-value.createdAt;
  return protocol==='anyconnect'&&value.platform===nativePlatform&&age>=0&&age<60000;
 }catch{return false;}
})();
let clientInstalled=clientHandoff;
const clientReady=()=>protocol!=='anyconnect'||clientInstalled;
const clientCopy=()=>{
 const name=nativePlatform==='windows'?'OpenConnect GUI':'Cisco Secure Client';
 return {
 ru:{install:'Установить '+name,confirmed:name+' установлен',required:'Подтвердите установку клиента, чтобы продолжить.'},
 en:{install:'Install '+name,confirmed:name+' is installed',required:'Confirm client installation to continue.'},
 lv:{install:'Instalēt '+name,confirmed:name+' ir instalēts',required:'Lai turpinātu, apstipriniet klienta instalēšanu.'}
 }[lang];
};
$('quickClientConfirmed').onchange=()=>{
 clientInstalled=$('quickClientConfirmed').checked;
 if(!clientInstalled){ocGrant=null;ocConfirmed=false;ocImported=false;clearTimeout(ocExpiryTimer);}
 if(ocDevice && nativePlatform!=='ios' && clientInstalled)panels('ocDelivery');else render();
};

let uncertain = get('quickRegistration') === 'pending';
let loadNumber = 0;
const suggestedPasskeyName = /iPad/i.test(navigator.userAgent) || (navigator.platform==='MacIntel' && navigator.maxTouchPoints>1) ? 'iPad' : nativePlatform==='ios'?'iPhone':nativePlatform==='windows'?'Windows':'Android';
$('passkeyName').value = suggestedPasskeyName;
function message(key, error = false) { messageKey = key; failed = error; render(); }
function persist() { if(protocol==='anyconnect')put('quickIngress',requestedIngress); put('quickServer', server); put('quickPlatform', platform);put('quickProtocol',protocol); }
function render() {
 if(server==='us')iosButtons=false;
 $('prepare').hidden = protocol === 'anyconnect' && nativePlatform === 'ios' && iosButtons && !!ocDevice;
 const options = $('iosVpnButtons');
 $('iosProfileSave').replaceChildren();
 options.hidden = !(protocol === 'anyconnect' && nativePlatform === 'ios') || server==='us' || !clientReady();
 if (!options.hidden) {
   const url = ocDevice ? new URL(API+'/oc/access/devices/'+encodeURIComponent(ocDevice.id)+'/ios.mobileconfig') : null;
   if (url) url.searchParams.set('ingress', server);
   options.replaceChildren(window.tolfIosButtons.create({checked:iosButtons, disabled:busy, lang,
     vpnName:ocDevice ? 'TOLF '+(server==='moscow'?'Moscow':'Riga') : null,
     url:url?.href, includeInstall:true, saveHost:$('iosProfileSave'), onChange:checked => {iosButtons = checked; saveIosSetup(); put('quickIosButtons', checked ? 'true' : ''); render();}
   }));
 }
 document.documentElement.lang = lang;
 $('quickProtocolName').textContent=protocol==='anyconnect'?'AnyConnect':'IKEv2';
 const back=document.getElementById('backHome');
 if(back){back.href='/?lang='+lang;back.setAttribute('aria-label',({ru:'Назад в Мой VPN',en:'Back to My VPN',lv:'Atpakaļ uz Mans VPN'})[lang]);}
 document.querySelectorAll('[data-text]').forEach(el => el.textContent = t(el.dataset.text));
 $('passkeyHelp').textContent = accountText[lang][2];
 if(protocol==='anyconnect' && nativePlatform==='windows'){
  const copy=OC_WINDOWS_TEXT[lang];
  $('ocReturn').textContent=copy.start;
  $('ocWindowsConnection').textContent=copy.fields;
  $('ocWindowsDefaults').textContent=copy.defaults;
  $('ocWindowsCertificate').textContent=copy.certificate;
  $('ocEnable').textContent=copy.enable;
  for(const id of ['ocCopyName','ocCopyGateway']){$(id).textContent=copy.copy;$(id).disabled=busy;}
 }
 if (protocol === 'anyconnect' && platform === 'ios') {
   $('prepare').textContent = t('ocIosInstall');
   const hint=document.querySelector('[data-text="defaults"]');
   if(hint){hint.textContent=t('ocIosInstallHelp');hint.style.whiteSpace='pre-line';}
 }
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
 const cc=clientCopy();
 $('quickClientInstall').hidden=true;
 $('quickClientConfirmed').checked=clientInstalled;
 $('quickClientConfirmed').disabled=busy;
 $('quickClientConfirmedLabel').textContent=cc.confirmed;
 $('quickClientRequired').textContent=clientInstalled?'':cc.required;
 $('ocApp').textContent=cc.install;
 $('ocApp').href=nativePlatform==='ios'?'https://apps.apple.com/app/id1135064690':nativePlatform==='android'?'https://play.google.com/store/apps/details?id=com.cisco.anyconnect.vpn.android.avf':'https://www.infradead.org/openconnect-gui/download/openconnect-gui-1.6.2-win64.exe';
 $('ocControl').hidden=nativePlatform==='windows';
 $('prepare').disabled ||= !clientReady();
 if(!clientReady()){$('ocDelivery').hidden=true;$('iosProfileSave').replaceChildren();}


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
 if(error?.certificateCheck)return t('ocGrantInvalid')+' '+error.certificateCheck;
 if(error && error.message==='Download failed')return 'ocDownloadFailed';
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
 if(protocol==='anyconnect' && nativePlatform==='ios'){
  let saved; try { saved=JSON.parse(get(ocKey('setup'),'null')); } catch {}
  if(saved && saved.expires>Date.now() && Object.hasOwn(OC_HOSTS,saved.server) && (!requestedIngress || requestedIngress===saved.server)){
   const caps=await api('/oc/access/capabilities');
   const point=caps.ingresses?.find(p=>p.id===saved.server);
   const list=await api('/oc/access/devices');
   const device=list.devices?.find(d=>d.id===saved.device && d.state==='active' && Date.parse(d.expires_at)>Date.now());
   if(point && point.host===OC_HOSTS[saved.server] && device){server=saved.server;ocPoint=point;ocDevice=device;iosButtons=saved.server!=='us' && saved.buttons===true;persist();}
   else put(ocKey('setup'),'');
  }
 }
 panels('preparePanel');
}
function saveIosSetup(){
 if(accountId && ocDevice && nativePlatform==='ios')
  put(ocKey('setup'),JSON.stringify({server,device:ocDevice.id,buttons:iosButtons,expires:Date.now()+7200000}));
}
async function initialize() {
 const number=++loadNumber;
 busy=true; panels(''); message('loading');
 try {
  if(windowsQuickBlocked){ready=false;message('windowsQuickOnly');return;}
  const capabilities=await api('/quick-setup/capabilities');
  if(capabilities.version!==1) throw new Error('Unavailable');
  if(!nativePlatform){ready=false;message('unsupportedDevice',true);return;}
  const r=await fetch(API+'/entry-point-recommendation',{credentials:'omit',cache:'no-store',signal:AbortSignal.timeout(6000)});
  if(!r.ok)throw new Error('Recommendation unavailable');
  const recommendation=await r.json();
  server=protocol==='anyconnect'&&requestedIngress?requestedIngress:recommendation.entryPoint;
  if(!(protocol==='anyconnect'?Object.hasOwn(OC_HOSTS,server):['riga','moscow'].includes(server)))throw new Error('Invalid recommendation');
  platform=nativePlatform;ready=true;
  if(protocol==='anyconnect'){
   const oc=await api('/oc/access/capabilities');
   ocPoint=oc.ingresses?.find(p=>p.id===server);
   if(oc.issuance!==true||!ocPoint||ocPoint.host!==OC_HOSTS[server])throw new Error('AnyConnect node unavailable');
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
 if(!clientReady()||!authenticated||!ready||!nativePlatform||(windowsQuickBlocked))return;
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
window.addEventListener('pageshow',e=>{if(!e.persisted)render();if(e.persisted && nativePlatform==='ios' && iosButtons && ocDevice){render();return;}if(e.persisted){profile='';ocGrant=null;ocDevice=null;ocConfirmed=false;ocImported=false;$('code').value='';initialize();}});

function ocKey(suffix){return 'quickOc:'+accountId+':'+nativePlatform+':'+suffix;}
// POST /import issues a fresh two-hour grant. The server enforces expiry;
// use elapsed time locally so an incorrect Windows clock cannot reject it.
const OC_GRANT_LIFETIME=2*60*60*1000;
const ocGrantValid=grant=>!!grant&&Number.isFinite(grant.localDeadline)&&performance.now()<grant.localDeadline;
function certificateCheck(code){throw Object.assign(new Error('Certificate validation failed'),{certificateCheck:code});}
function validateOcGrant(grant){
 const point=grant.connections?.find(p=>p.id===server);
 if(!point)certificateCheck('entry_missing');
 if(typeof grant.password!=='string'||!grant.password)certificateCheck('password_missing');
 if(!Number.isFinite(Date.parse(grant.expiresAt)))certificateCheck('expiry_format');
 let certificate;
 try{certificate=new URL(grant.certificateUrl);}catch{certificateCheck('download_url_format');}
 if(certificate.protocol!=='https:'||certificate.hostname!=='api.tolf.is'||certificate.username||certificate.password||!certificate.pathname.startsWith('/oc/access/import/'))certificateCheck('download_url_identity');
 // Windows downloads PKCS12 directly. Cisco application links are mobile-only.
 if(nativePlatform!=='windows'){
  let connect,importLink;
  try{connect=new URL(point.connectionUri);importLink=new URL(grant.importUri);}catch{certificateCheck('mobile_url_format');}
  if(connect.protocol!=='anyconnect:'||connect.hostname!=='create')certificateCheck('mobile_connection_scheme');
  if(connect.searchParams.get('host')!==point.host||connect.searchParams.get('certcommonname')!==grant.username)certificateCheck('mobile_connection_identity');
  if(importLink.protocol!=='anyconnect:'||importLink.hostname!=='import'||importLink.searchParams.get('uri')!==grant.certificateUrl)certificateCheck('mobile_import_identity');
 }
 return point;
}
async function prepareOc(){
 if(!clientReady())return;
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
 if(nativePlatform==='ios'){
  saveIosSetup();
  const url=new URL(API+'/oc/access/devices/'+encodeURIComponent(ocDevice.id)+'/ios.mobileconfig');
  url.searchParams.set('ingress',server);
  locked=false;
  // Single real user click on the Quick Setup primary action:
  // prepare/reuse device identity, then navigate to authenticated
  // HTTPS MobileConfig directly. No extra page or PKCS12 import.
  if (iosButtons) {
    panels('preparePanel');
    message('');
    return;
  }
  window.location.assign(window.tolfIosButtons.profileUrl(url.href, false));
  message('started');
  return;
 }
 ocConfirmed=false;ocImported=false;ocGrant=null;
 panels('ocDelivery');message('');
}
async function prepareOcImport(){
 if(!clientReady()||!ocDevice||!ocConfirmed)return;
 ocImported=false;ocGrant=null;
 const deviceId=ocDevice.id;
 const started=performance.now();
 const grant=await api('/oc/access/devices/'+encodeURIComponent(deviceId)+'/import',{method:'POST',body:'{}'});
 grant.localDeadline=started+OC_GRANT_LIFETIME;
 if(grant.deviceId!==deviceId)certificateCheck('device_identity');
 const point=validateOcGrant(grant);
 if(point.host!==ocPoint.host)certificateCheck('entry_identity');
 if(grant.username!==ocDevice.username)certificateCheck('certificate_identity');
 ocGrant=grant;
 clearTimeout(ocExpiryTimer);ocExpiryTimer=setTimeout(()=>{if(ocGrant===grant)render();},Math.max(0,grant.localDeadline-performance.now()));
 panels('ocDelivery');message('');
}
function renderOcDelivery(){
 const mobile=nativePlatform!=='windows',valid=ocGrantValid(ocGrant)&&ocConfirmed&&!ocImported;
 $('ocApp').href=nativePlatform==='ios'?'https://apps.apple.com/app/id1135064690':nativePlatform==='android'?'https://play.google.com/store/apps/details?id=com.cisco.anyconnect.vpn.android.avf':'https://www.infradead.org/openconnect-gui/download/openconnect-gui-1.6.2-win64.exe';
 const prefix='TOLF '+({riga:'Riga',moscow:'Moscow',us:'New York'}[server])+' ';
 const name=ocDevice.connectionNames?.[server]||Array.from(prefix+ocDevice.label).slice(0,24).join('').trimEnd();
 $('ocConnection').href='anyconnect://create/?'+new URLSearchParams({name,host:ocPoint.host,usecert:'true',certcommonname:ocDevice.username,netroam:'true'});
 $('ocServer').textContent=t(server)+': '+ocPoint.host;
 $('ocWindowsFields').hidden=mobile;
 $('ocWindowsName').value=name;
 $('ocWindowsGateway').value='https://'+ocPoint.host;
 $('ocConnection').hidden=!mobile;
 $('ocConnectionActions').hidden=ocConfirmed;$('ocConnectionCompleted').hidden=!ocConfirmed;
 for(const id of ['ocConfirmConnection','ocAgain'])$(id).disabled=busy;
 $('ocRenew').disabled=busy||!ocConfirmed;
 $('ocAlreadyImported').disabled=busy||!ocConfirmed;
 $('ocAlreadyImported').hidden=ocImported;
 $('ocCertificateDone').hidden=!ocImported;
 $('ocCertificateHint').textContent=t(!ocConfirmed?'ocBlocked':ocGrant&&!valid?'ocExpired':'ocCertificateHelp');
 if(!mobile){
  if(!ocConfirmed)$('ocCertificateHint').textContent=({ru:'Сначала сохраните профиль в OpenConnect GUI и нажмите «Соединение добавлено».',en:'Save the OpenConnect GUI profile first, then select “Connection added”.',lv:'Vispirms saglabājiet OpenConnect GUI profilu un nospiediet “Savienojums pievienots”.'})[lang];
  else if(!(ocGrant&&!valid))$('ocCertificateHint').textContent=OC_WINDOWS_TEXT[lang].help;
 }
 $('ocGrantPanel').hidden=!valid;
 if(valid)$('ocImport').href=ocGrant.importUri;else $('ocImport').removeAttribute('href');
 $('ocImport').hidden=!mobile||!valid;
 $('ocControl').hidden=!mobile;$('ocWindowsConnection').hidden=mobile;$('ocWindowsCertificate').hidden=mobile||ocImported;
 $('ocPassword').value=valid?ocGrant.password:'';
 $('ocCopyPassword').setAttribute('aria-label',t('ocCopyPassword'));
 $('ocCopyPassword').title=t('ocCopyPassword');
 $('ocCopyPassword').disabled=busy||!valid;$('ocDownload').disabled=busy||!valid;
}
$('ocConfirmConnection').onclick=()=>{if(!clientReady()||busy||!ocDevice)return;ocConfirmed=true;message('');};
$('ocAgain').onclick=()=>{if(busy)return;ocConfirmed=false;ocImported=false;ocGrant=null;clearTimeout(ocExpiryTimer);message('');};
$('ocAlreadyImported').onclick=()=>{if(!clientReady()||busy||!ocConfirmed)return;ocImported=true;ocGrant=null;clearTimeout(ocExpiryTimer);message('');};
$('ocConnection').onclick=event=>{if(!clientReady()||busy||!ocDevice)event.preventDefault();};

for(const [button,input] of [['ocCopyName','ocWindowsName'],['ocCopyGateway','ocWindowsGateway']]){
 $(button).onclick=()=>action(async()=>{
  if(!ocDevice||nativePlatform!=='windows')return;
  try{await navigator.clipboard.writeText($(input).value);message('copied');}
  catch{$(input).focus();$(input).select();message('');}
 });
}
$('ocCopyPassword').onclick=()=>action(async()=>{if(!clientReady()||!ocGrantValid(ocGrant))throw Error('Expired');await navigator.clipboard.writeText(ocGrant.password);message('copied');});
$('ocImport').onclick=event=>{if(!clientReady()||!ocGrantValid(ocGrant)){event.preventDefault();message('ocExpired',true);}};
$('ocRenew').onclick=()=>action(prepareOcImport);
$('ocDownload').onclick=()=>action(async()=>{
 if(!clientReady()||!ocGrantValid(ocGrant))throw Error('Expired');
 const response=await fetch(ocGrant.certificateUrl,{credentials:'omit',cache:'no-store',signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw Error('Download failed');
 const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');
 a.href=url;a.download='TOLF-AnyConnect.p12';document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);message('started');
});

render();
if(protocol==='anyconnect'&&!clientHandoff&&!windowsQuickBlocked){
 put('tolfTransport','anyconnect');
 window.location.assign('/?lang='+encodeURIComponent(lang));
}else initialize();
})();

