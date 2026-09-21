
const $=id=>document.getElementById(id);
const passkeyList=$('passkeyList'), passkeyMessage=$('passkeyMessage'), addPasskeyButton=$('addPasskeyButton'), deleteAccountButton=$('deleteAccountButton');
const generateRecoveryButton=$('generateRecoveryButton'), accountRecoveryCode=$('accountRecoveryCode'), accountRecoveryBox=$('accountRecoveryBox'), copyAccountRecoveryButton=$('copyAccountRecoveryButton'), savedAccountRecoveryButton=$('savedAccountRecoveryButton'), recoveryMessage=$('recoveryMessage');
for(const [lang,title] of Object.entries({en:'TOLF Account',ru:'Аккаунт TOLF',lv:'TOLF konts'})) Object.assign(I18N[lang],{accountTitle:title});
function t(key,replacements={}){let value=I18N[currentLanguage]?.[key]??I18N.en[key]??key;for(const [k,v] of Object.entries(replacements))value=value.replaceAll('{'+k+'}',v);return value;}
function confirmLocalized(title,body,replacements={}){return confirm(t(title)+'\n\n'+t(body,replacements));}
function setLanguage(lang){
 if(!['en','ru','lv'].includes(lang))return;
 currentLanguage=lang;document.documentElement.lang=lang;
 try{localStorage.setItem('tolfLanguage',lang);localStorage.setItem('tolf-language',lang);}catch{}
 document.querySelectorAll('[data-i18n]').forEach(e=>e.textContent=t(e.dataset.i18n));
 for(const key of ['en','ru','lv']){$('lang'+key[0].toUpperCase()+key.slice(1)).setAttribute('aria-pressed',String(key===lang));}
 $('backHome').href='https://tolf.is/?lang='+lang;
 $('backHome').setAttribute('aria-label',{en:'TOLF home',ru:'На главную TOLF',lv:'Uz TOLF sākumlapu'}[lang]);
 $('vpnNavigation').href='../?lang='+lang;document.title=t('accountTitle');
 const url=new URL(location.href);url.searchParams.set('lang',lang);history.replaceState(null,'',url);
 if(lastPasskeys.length)renderPasskeys(lastPasskeys);
}
async function apiRequest(path,options={}){
 const response=await fetch(API+path,{credentials:'include',cache:'no-store',...options,headers:{'Content-Type':'application/json',...options.headers}});
 let data=null;try{data=await response.json();}catch{}
 if(!response.ok){const e=new Error(data?.detail||t('requestFailed'));e.status=response.status;throw e;}return data;
}
async function copyText(value){
 try{await navigator.clipboard.writeText(value);return;}catch{}
 const el=document.createElement('textarea');el.value=value;el.style.position='fixed';el.style.opacity='0';document.body.append(el);el.select();
 let copied=false;try{copied=document.execCommand('copy');}finally{el.remove();}if(!copied)throw Error('copy_failed');
}
function showAccountRecoveryCode(code){accountRecoveryCode.textContent=code;accountRecoveryBox.classList.remove('hidden');}
function hideAccountRecoveryCode(){accountRecoveryCode.textContent='';accountRecoveryBox.classList.add('hidden');}
function signIn(){location.replace('../auth/?mode=signin&next=account&lang='+currentLanguage);}
async function loadSettings(){
 try{await apiRequest('/me');}
 catch(e){if(e.status===401){signIn();return;}$('accountStatus').textContent=e.message;return;}
 $('accountContent').classList.remove('hidden');
 await Promise.all([loadAccountPassword(),loadPasskeys(),apiRequest('/vpn/invitations/status').then(d=>{invitationProtected=d.protected===true;}).catch(()=>{})]);
}
$('accountSignOut').onclick=async()=>{
 $('accountSignOut').disabled=true;
 try{await apiRequest('/logout',{method:'POST',body:'{}'});clearAccountPassword();hideAccountRecoveryCode();location.assign('https://tolf.is/?lang='+currentLanguage);}
 catch(e){$('accountStatus').textContent=e.message;$('accountSignOut').disabled=false;}
};
deleteAccountButton.onclick=async()=>{
 if(invitationProtected){alert(t('protectedAccountDelete'));return;}
 if(!confirmLocalized('deleteAccountConfirmTitle','deleteAccountConfirmBody'))return;
 deleteAccountButton.disabled=true;$('accountStatus').textContent=t('deletingAccount');
 try{await apiRequest('/account/delete',{method:'POST',body:JSON.stringify({confirm:'DELETE'})});clearAccountPassword();hideAccountRecoveryCode();$('accountContent').classList.add('hidden');$('accountSignOut').classList.add('hidden');$('accountStatus').textContent=t('accountDeleted');}
 catch(e){$('accountStatus').textContent=e.message;}finally{deleteAccountButton.disabled=false;}
};
for(const lang of ['en','ru','lv'])$('lang'+lang[0].toUpperCase()+lang.slice(1)).onclick=()=>setLanguage(lang);
setLanguage(currentLanguage);
window.addEventListener('DOMContentLoaded',loadSettings,{once:true});
window.addEventListener('pagehide',hideAccountRecoveryCode);
window.addEventListener('pageshow',e=>{if(e.persisted)loadSettings();});
