(() => {
  'use strict';
  const card = document.querySelector('.trial-card');
  if (!card || !window.TolfBillingVolume) return;
  const words = {
    ru:{register:'Оформить пробный аккаунт',notice:'Пробный пакет 1 ГБ пока не выдаётся.',registered:'Пробная регистрация оформлена: ',error:'Не удалось проверить или сохранить пробную регистрацию. Попробуйте ещё раз.',working:'Сохраняем…'},
    en:{register:'Register a trial account',notice:'The 1 GB trial package is not available yet.',registered:'Trial registration recorded: ',error:'Could not check or save the trial registration. Try again.',working:'Saving…'},
    lv:{register:'Reģistrēt izmēģinājuma kontu',notice:'1 GB izmēģinājuma paka vēl nav pieejama.',registered:'Izmēģinājuma reģistrācija saglabāta: ',error:'Neizdevās pārbaudīt vai saglabāt izmēģinājuma reģistrāciju. Mēģiniet vēlreiz.',working:'Saglabāšana…'}
  };
  const lang = () => words[document.documentElement.lang] ? document.documentElement.lang : 'en';
  const panel = document.createElement('div'), status = document.createElement('p'), button = document.createElement('button');
  panel.className='trial-registration'; status.className='muted'; status.setAttribute('role','status'); button.type='button'; button.className='billing-secondary secondary';
  panel.append(status,button);card.appendChild(panel);
  let authenticated=false, trial=null, busy=false, error=false;
  async function api(method,body) {
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
    try { const r=await fetch('https://api.tolf.is/account/trial-registration',{method,credentials:'include',cache:'no-store',signal:controller.signal,headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})}); if(!r.ok){const e=new Error();e.status=r.status;throw e;}return await r.json(); }
    finally {clearTimeout(timeout);}
  }
  function render() {
    const t=words[lang()];panel.hidden=!window.TolfBillingVolume.isTrial();button.hidden=!!trial;button.disabled=busy;
    button.textContent=busy?t.working:t.register;
    status.textContent=error?t.error:trial?t.registered+new Date(trial.registeredAt).toLocaleString(lang())+'. '+t.notice:t.notice;
  }
  button.addEventListener('click',async()=>{
    if(busy)return;
    if(!authenticated){location.assign('/auth/?mode=signup&next=billing&purpose=trial&lang='+lang());return;}
    busy=true;error=false;render();
    try{const data=await api('POST',{confirm:'TRIAL_REGISTRATION'});trial=data.trialRegistration;}
    catch{error=true;}finally{busy=false;render();}
  });
  window.addEventListener('tolf:billing-render',render);
  const requested=new URL(location.href).searchParams.get('trial');
  if(requested==='1'&&!window.TolfBillingVolume.isTrial())document.getElementById('selectTrial').click();
  render();
  api('GET').then(data=>{authenticated=true;trial=data.trialRegistration;render();}).catch(e=>{if(e.status!==401)error=true;render();});
})();
