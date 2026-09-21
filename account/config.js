const API="https://api.tolf.is";
const I18N={};
let currentLanguage=new URL(location.href).searchParams.get('lang');
try { currentLanguage=currentLanguage||localStorage.getItem('tolfLanguage'); } catch {}
if(!['en','ru','lv'].includes(currentLanguage)) currentLanguage=/^ru/i.test(navigator.language)?'ru':/^lv/i.test(navigator.language)?'lv':'en';
let lastPasskeys=[];
let invitationProtected=false;
