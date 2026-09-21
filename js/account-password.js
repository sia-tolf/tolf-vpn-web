(() => {
'use strict';
const $=id=>document.getElementById(id);
const words={
 en:{title:'Username and password',help:'Another way to sign in to this same TOLF account. This password is separate from your VPN passwords.',username:'Username',copyLogin:'Copy username',change:'Set a new password',add:'Add username and password',none:'Password sign-in is not set up yet.',loginHelp:'3–32 Latin letters, numbers, dots, hyphens or underscores. Start with a letter or number.',password:'New account password',passwordHelp:'15–128 characters. Generate a password or enter your own; you can edit a generated password.',generate:'Generate',show:'Show password',hide:'Hide password',save:'Save password',cancel:'Cancel',impact:'Your current login remains active. Other account sessions will be signed out. Passkeys, recovery code and VPN profiles stay unchanged.',created:'Password saved. Copy your sign-in details now.',once:'These details are available until you close this block or leave the page. You can copy them more than once. The old password cannot be retrieved later.',copy:'Copy sign-in details',saved:'I saved the details',copied:'Copied.',manual:'Select and copy the text below.',working:'Saving…',error:'Could not save. Please try again.',username_taken:'This username is already taken.',invalid_username:'Use 3–32 Latin letters, numbers, dots, hyphens or underscores.',invalid_password:'Use 15–128 characters.',weak_password:'Choose a less predictable password or generate one.',too_many_attempts:'Too many attempts. Try again in 15 minutes.',try_later:'Try again in a few seconds.',authentication_required:'Your session has expired. Sign in again.'},
 ru:{title:'Логин и пароль',help:'Ещё один способ входа в этот же аккаунт TOLF. Этот пароль отличается от паролей VPN.',username:'Логин',copyLogin:'Скопировать логин',change:'Задать новый пароль',add:'Добавить логин и пароль',none:'Вход по паролю пока не настроен.',loginHelp:'3–32 латинские буквы, цифры, точки, дефисы или подчёркивания. Первый символ — буква или цифра.',password:'Новый пароль аккаунта',passwordHelp:'От 15 до 128 символов. Сгенерируйте пароль или введите свой; сгенерированный пароль можно изменить.',generate:'Сгенерировать',show:'Показать пароль',hide:'Скрыть пароль',save:'Сохранить пароль',cancel:'Отмена',impact:'Текущий вход сохранится. Другие сеансы входа в аккаунт будут закрыты. Passkey, код восстановления и VPN-профили не изменятся.',created:'Пароль сохранён. Теперь скопируйте данные для входа.',once:'Данные доступны, пока вы не закроете этот блок или страницу. Копировать можно несколько раз. Позже посмотреть прежний пароль не получится.',copy:'Скопировать данные',saved:'Я сохранил данные',copied:'Скопировано.',manual:'Выделите и скопируйте текст ниже.',working:'Сохранение…',error:'Не удалось сохранить. Повторите попытку.',username_taken:'Этот логин уже занят.',invalid_username:'Используйте 3–32 латинские буквы, цифры, точки, дефисы или подчёркивания.',invalid_password:'Длина пароля — от 15 до 128 символов.',weak_password:'Выберите менее предсказуемый пароль или сгенерируйте его.',too_many_attempts:'Слишком много попыток. Повторите через 15 минут.',try_later:'Повторите через несколько секунд.',authentication_required:'Сеанс завершён. Войдите в аккаунт снова.'},
 lv:{title:'Lietotājvārds un parole',help:'Vēl viens veids, kā pieteikties šajā pašā TOLF kontā. Šī parole atšķiras no VPN parolēm.',username:'Lietotājvārds',copyLogin:'Kopēt lietotājvārdu',change:'Iestatīt jaunu paroli',add:'Pievienot lietotājvārdu un paroli',none:'Pieteikšanās ar paroli vēl nav iestatīta.',loginHelp:'3–32 latīņu burti, cipari, punkti, defises vai pasvītrojumi. Sāciet ar burtu vai ciparu.',password:'Jaunā konta parole',passwordHelp:'15–128 rakstzīmes. Ģenerējiet paroli vai ievadiet savu; ģenerēto paroli var rediģēt.',generate:'Ģenerēt',show:'Rādīt paroli',hide:'Paslēpt paroli',save:'Saglabāt paroli',cancel:'Atcelt',impact:'Pašreizējā sesija paliks aktīva. Pārējās konta sesijas tiks slēgtas. Passkey, atkopšanas kods un VPN profili nemainīsies.',created:'Parole saglabāta. Tagad nokopējiet piekļuves datus.',once:'Dati ir pieejami, kamēr neaizverat šo bloku vai lapu. Tos var kopēt vairākkārt. Vēlāk iepriekšējo paroli apskatīt nevarēs.',copy:'Kopēt piekļuves datus',saved:'Dati ir saglabāti',copied:'Nokopēts.',manual:'Atlasiet un kopējiet tekstu zemāk.',working:'Saglabā…',error:'Neizdevās saglabāt. Mēģiniet vēlreiz.',username_taken:'Šis lietotājvārds jau ir aizņemts.',invalid_username:'Izmantojiet 3–32 latīņu burtus, ciparus, punktus, defises vai pasvītrojumus.',invalid_password:'Izmantojiet 15–128 rakstzīmes.',weak_password:'Izvēlieties grūtāk uzminamu paroli vai ģenerējiet to.',too_many_attempts:'Pārāk daudz mēģinājumu. Mēģiniet pēc 15 minūtēm.',try_later:'Mēģiniet pēc dažām sekundēm.',authentication_required:'Sesija ir beigusies. Piesakieties vēlreiz.'}
};
let login=null, busy=false, details=null, generation=0;
const section=$('accountPasswordSection');
const tr=key=>(words[document.documentElement.lang]||words.en)[key]||words.en[key]||words.en.error;
function render(){
 section.querySelectorAll('[data-password-text]').forEach(el=>el.textContent=tr(el.dataset.passwordText));
 $('apOpen').textContent=tr(login?'change':'add');
 $('apToggle').textContent=tr($('apPassword').type==='password'?'show':'hide');
 $('apCredentials').value=details?'TOLF — https://vpn.tolf.is/auth/\n'+tr('username')+': '+details.username+'\n'+tr('password')+': '+details.password:'';
}
new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
async function api(path,body){
 const response=await fetch('https://api.tolf.is'+path,{method:body?'POST':'GET',credentials:'include',cache:'no-store',headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
 const data=await response.json();
 if(!response.ok)throw new Error(response.status===401?'authentication_required':data.detail);
 return data;
}
window.loadAccountPassword=async()=>{
 const request=++generation;
 try {
  const data=await api('/password/account');
  if(request!==generation)return;
  login=data.enabled?data.username:null;
  $('apLogin').value=login||'';
  $('apExisting').classList.toggle('hidden',!login);
  $('apNone').classList.toggle('hidden',Boolean(login));
  section.classList.remove('hidden');render();
 }catch{if(request===generation)section.classList.add('hidden');}
};
window.clearAccountPassword=()=>{
 generation++;details=null;login=null;
 $('apPassword').value='';$('apCredentials').value='';$('apLogin').value='';$('apNewLogin').value='';
 $('apForm').classList.add('hidden');$('apResult').classList.add('hidden');$('apOpen').classList.remove('hidden');
 $('apMessage').textContent='';section.classList.add('hidden');
};
function message(key){$('apMessage').textContent=tr(key);}
async function copy(value,field){
 try {await navigator.clipboard.writeText(value);message('copied');return;}catch{}
 const temp=document.createElement('textarea');temp.value=value;temp.style.position='fixed';temp.style.opacity='0';document.body.appendChild(temp);temp.select();
 let ok=false;try{ok=document.execCommand('copy');}catch{}temp.remove();
 if(ok)message('copied');else{field.focus();field.select();message('manual');}
}
$('apCopyLogin').onclick=()=>copy(login,$('apLogin'));
$('apOpen').onclick=()=>{
 $('apNewLoginGroup').classList.toggle('hidden',Boolean(login));$('apNewLogin').required=!login;
 $('apForm').classList.remove('hidden');$('apOpen').classList.add('hidden');$('apMessage').textContent='';
 (login?$('apPassword'):$('apNewLogin')).focus();
};
$('apCancel').onclick=()=>{$('apPassword').value='';$('apForm').classList.add('hidden');$('apOpen').classList.remove('hidden');};
$('apToggle').onclick=()=>{$('apPassword').type=$('apPassword').type==='password'?'text':'password';render();};
$('apGenerate').onclick=()=>{
 const chars='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
 $('apPassword').value=Array.from(crypto.getRandomValues(new Uint8Array(20)),b=>chars[b&63]).join('');
 $('apPassword').type='text';render();$('apPassword').focus();
};
$('apForm').onsubmit=async event=>{
 event.preventDefault();if(busy)return;
 busy=true;section.querySelectorAll('button,input').forEach(el=>el.disabled=true);message('working');
 const value=$('apPassword').value, request=generation;
 try{
  const data=await api('/password/set',{username:login||$('apNewLogin').value.toLowerCase(),password:value});
  if(request!==generation)return;
  login=data.username;details={username:login,password:value};
  $('apLogin').value=login;$('apExisting').classList.remove('hidden');$('apNone').classList.add('hidden');
  $('apPassword').value='';$('apForm').classList.add('hidden');$('apResult').classList.remove('hidden');render();message('created');
 }catch(error){message(error.message);}
 finally{busy=false;section.querySelectorAll('button,input').forEach(el=>el.disabled=false);}
};
$('apCopyDetails').onclick=()=>copy($('apCredentials').value,$('apCredentials'));
$('apSaved').onclick=()=>{details=null;$('apCredentials').value='';$('apResult').classList.add('hidden');$('apOpen').classList.remove('hidden');$('apMessage').textContent='';};
window.addEventListener('beforeunload',event=>{if(details){event.preventDefault();event.returnValue='';}});
window.addEventListener('pagehide',()=>{window.clearAccountPassword();});
window.addEventListener('pageshow',event=>{if(event.persisted)window.loadAccountPassword();});
render();
})();
