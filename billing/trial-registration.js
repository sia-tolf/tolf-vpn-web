(() => {
  'use strict';
  const card = document.querySelector('.trial-card');
  if (!card || !window.TolfBillingVolume) return;
  const words = {
    ru:{claim:'Получить 1 ГБ бесплатно',notice:'1 ГБ бесплатно, один раз на аккаунт. Без ограничения по времени.',remaining:'Остаток пробного трафика',gb:'ГБ',active:'Пробный пакет активен. Остаток обновляется автоматически по данным серверов.',exhausted:'Пробный трафик закончился. Для продолжения VPN пополните оплаченный трафик.',paid:'Пробный трафик закончился. Используется оплаченный пакет.',unavailable:'Пробный пакет предназначен для новых аккаунтов без покупок. Ваш текущий доступ сохраняется.',error:'Не удалось обновить остаток. Показаны последние полученные данные.',working:'Начисляем…',loading:'Проверяем пробный пакет…'},
    en:{claim:'Get 1 GB for free',notice:'1 GB free, once per account. No expiry date.',remaining:'Trial traffic remaining',gb:'GB',active:'Your trial is active. The balance updates automatically from server reports.',exhausted:'Your trial traffic is used up. Add paid traffic to continue using VPN.',paid:'Your trial traffic is used up. Your paid package is being used.',unavailable:'The trial is for new accounts without purchases. Your existing access is unchanged.',error:'Could not refresh the balance. Showing the last received data.',working:'Activating…',loading:'Checking your trial…'},
    lv:{claim:'Saņemt 1 GB bez maksas',notice:'1 GB bez maksas, vienu reizi katram kontam. Bez derīguma termiņa.',remaining:'Atlikušais izmēģinājuma datu apjoms',gb:'GB',active:'Izmēģinājuma paka ir aktīva. Atlikums automātiski atjaunojas pēc serveru datiem.',exhausted:'Izmēģinājuma dati ir iztērēti. Lai turpinātu lietot VPN, papildiniet apmaksāto datu apjomu.',paid:'Izmēģinājuma dati ir iztērēti. Tiek izmantota apmaksātā paka.',unavailable:'Izmēģinājums ir paredzēts jauniem kontiem bez pirkumiem. Esošā piekļuve nemainās.',error:'Neizdevās atjaunināt atlikumu. Redzami pēdējie saņemtie dati.',working:'Aktivizēšana…',loading:'Pārbaudām izmēģinājuma paku…'}
  };
  const lang=()=>words[document.documentElement.lang]?document.documentElement.lang:'en';
  const panel=document.createElement('div'),label=document.createElement('p'),balance=document.createElement('strong'),status=document.createElement('p'),button=document.createElement('button');
  panel.className='trial-registration';label.className='muted';balance.className='trial-balance';status.className='muted';status.setAttribute('role','status');button.type='button';button.className='billing-secondary secondary';
  panel.append(label,balance,status,button);card.appendChild(panel);
  let authenticated=false,data=null,busy=false,error=false,loading=true,inflight=false;
  async function api(method,body){
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
    try{const r=await fetch('https://api.tolf.is/account/trial-package',{method,credentials:'include',cache:'no-store',signal:controller.signal,headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});if(!r.ok){const e=new Error();e.status=r.status;throw e;}return await r.json();}
    finally{clearTimeout(timeout);}
  }
  function render(){
    const t=words[lang()],p=data?.trialPackage,trial=window.TolfBillingVolume.isTrial();
    panel.hidden=!trial&&!p;label.hidden=balance.hidden=!p;
    label.textContent=t.remaining;
    balance.textContent=p?new Intl.NumberFormat(lang(),{minimumFractionDigits:3,maximumFractionDigits:3}).format(p.balanceBytes/1e9)+' '+t.gb:'';
    button.hidden=!!p||(!trial)||!!(authenticated&&data&&!data.canClaim);button.disabled=busy||loading;
    button.textContent=busy?t.working:t.claim;
    status.textContent=(error?t.error+' ':'')+(loading?t.loading:p?(p.balanceBytes>0?t.active:p.paidBalanceBytes>0?t.paid:t.exhausted):authenticated&&data&&!data.canClaim?t.unavailable:t.notice);
    document.querySelector('.billing-layout').hidden=trial;
    const note=document.querySelector('.preview-note');if(note)note.hidden=trial;
    const select=document.getElementById('selectTrial');if(select)select.hidden=trial;
  }
  async function refresh(){
    if(inflight||busy||document.hidden)return;
    inflight=true;
    try{data=await api('GET');authenticated=true;error=false;}
    catch(e){if(e.status===401){authenticated=false;data=null;error=false;}else error=true;}
    finally{loading=false;inflight=false;render();}
  }
  button.addEventListener('click',async()=>{
    if(busy||loading||inflight)return;
    if(!authenticated){location.assign('/auth/?mode=signup&next=billing&purpose=trial&lang='+lang());return;}
    busy=true;error=false;render();
    try{data=await api('POST',{confirm:'CLAIM_TRIAL'});authenticated=true;}
    catch(e){if(e.status===401){authenticated=false;data=null;}error=true;}
    finally{busy=false;render();}
  });
  window.addEventListener('tolf:billing-render',render);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  setInterval(refresh,15000);
  if(new URL(location.href).searchParams.get('trial')==='1'&&!window.TolfBillingVolume.isTrial())document.getElementById('selectTrial').click();
  render();refresh();
})();
