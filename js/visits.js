/* First-party page counts. Persistent browser recognition is optional. */
(() => {
  'use strict';
  if (location.origin !== 'https://vpn.tolf.is' || window.top !== window.self) return;
  const API = 'https://api.tolf.is', PREF = 'tolfAnalyticsChoice', BROWSER = 'tolfAnalyticsBrowser', EXCLUDE = 'tolfAnalyticsExcluded';
  const DAY = 86400000;
  const text = {
    en: {title:'Website statistics',note:'We count page openings without saving IP addresses. May we also recognise repeat visits in this browser for 30 days?',allow:'Allow recognition',basic:'Page counts only',settings:'Website statistics',excluded:'This browser is excluded from statistics.',privacy:'Privacy'},
    ru: {title:'Статистика посещений',note:'Мы считаем открытия страниц без сохранения IP-адресов. Разрешить также распознавать повторные посещения в этом браузере в течение 30 дней?',allow:'Разрешить распознавание',basic:'Только общий счётчик',settings:'Статистика посещений',excluded:'Этот браузер исключён из статистики.',privacy:'Приватность'},
    lv: {title:'Vietnes statistika',note:'Mēs skaitām lapu atvēršanas, nesaglabājot IP adreses. Vai atļaujat arī atpazīt atkārtotus apmeklējumus šajā pārlūkā 30 dienas?',allow:'Atļaut atpazīšanu',basic:'Tikai lapu skaitītājs',settings:'Vietnes statistika',excluded:'Šis pārlūks ir izslēgts no statistikas.',privacy:'Privātums'}
  };
  const get = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const put = (key, value) => { try { localStorage.setItem(key, value); return true; } catch { return false; } };
  const remove = key => { try { localStorage.removeItem(key); } catch {} };
  const excluded = () => get(EXCLUDE) === '1';
  const signal = () => navigator.globalPrivacyControl === true || navigator.doNotTrack === '1' || window.doNotTrack === '1';
  const lang = () => ['en','ru','lv'].includes(document.documentElement.lang) ? document.documentElement.lang : 'en';
  const tr = () => text[lang()];
  const uuid = () => typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, c => (Number(c) ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> Number(c) / 4).toString(16));
  let choice = null, panel, settings, timer, sent = false;
  try {
    const stored = JSON.parse(get(PREF));
    if (stored && stored.expires > Date.now() && typeof stored.allow === 'boolean') choice = stored.allow;
    else { remove(PREF); remove(BROWSER); }
  } catch { remove(BROWSER); }
  function exclude() {
    put(EXCLUDE, '1'); remove(BROWSER); clearTimeout(timer);
    if (panel) panel.hidden = true;
  }
  window.TolfVisits = {exclude, isExcluded:excluded};
  const requested = new URL(location.href);
  if (requested.searchParams.get('analytics') === 'exclude') {
    exclude(); requested.searchParams.delete('analytics');
    history.replaceState(history.state, '', requested.pathname + requested.search + requested.hash);
  }
  function identity() {
    if (choice !== true || signal()) return {};
    let stored;
    try { stored = JSON.parse(get(BROWSER)); } catch {}
    const now = Date.now(), valid = v => typeof v === 'string' && /^[0-9a-f-]{36}$/.test(v);
    if (!stored || stored.expires <= now || !valid(stored.id)) stored = {id:uuid(),expires:now + 30 * DAY};
    if (!valid(stored.visit) || !stored.lastSeen || now - stored.lastSeen > 1800000) stored.visit = uuid();
    stored.lastSeen = now;
    if (!put(BROWSER, JSON.stringify(stored))) return {};
    return {consent:true,browserId:stored.id,visitId:stored.visit};
  }
  async function count() {
    if (sent || excluded() || signal() || location.pathname.startsWith('/admin/') || document.visibilityState === 'hidden') return;
    sent = true;
    let referrer = '';
    try { referrer = new URL(document.referrer).hostname; } catch {}
    const payload = {eventId:uuid(),page:location.pathname,referrer,...identity()};
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const result = await fetch(API + '/analytics/view', {method:'POST',credentials:'include',cache:'no-store',keepalive:true,signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      if (result.ok && (await result.json()).excluded) exclude();
    } catch {} finally { clearTimeout(timeout); }
  }
  function choose(allow) {
    choice = allow; put(PREF, JSON.stringify({allow,expires:Date.now() + 180 * DAY}));
    if (!allow) remove(BROWSER);
    panel.hidden = true;
  }
  function render() {
    if (!panel) return;
    const t = tr();
    panel.querySelector('h2').textContent = t.title;
    panel.querySelector('p').textContent = excluded() ? t.excluded : t.note;
    panel.querySelector('[data-allow]').textContent = t.allow;
    panel.querySelector('[data-basic]').textContent = t.basic;
    panel.querySelectorAll('button').forEach(b => b.hidden = excluded());
    panel.querySelector('a').textContent = t.privacy;
    panel.querySelector('a').href = '/privacy.html?lang=' + lang();
    settings.textContent = t.settings;
  }
  function ready() {
    if (location.pathname.startsWith('/admin/') || excluded() || signal()) return;
    panel = document.createElement('section'); panel.className = 'tolf-visits-panel'; panel.setAttribute('aria-label', tr().title); panel.hidden = choice !== null;
    panel.innerHTML = '<h2></h2><p></p><div><button type="button" data-allow></button><button type="button" data-basic></button><a></a><button type="button" class="tolf-visits-close" aria-label="Close">×</button></div>';
    panel.querySelector('[data-allow]').addEventListener('click', () => choose(true));
    panel.querySelector('[data-basic]').addEventListener('click', () => choose(false));
    panel.querySelector('.tolf-visits-close').addEventListener('click', () => choose(false));
    settings = document.createElement('button'); settings.type = 'button'; settings.className = 'tolf-visits-settings';
    settings.addEventListener('click', () => { render(); panel.hidden = !panel.hidden; });
    const footer = document.querySelector('footer') || document.querySelector('main') || document.body;
    footer.appendChild(settings); document.body.appendChild(panel); render();
    new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
    timer = setTimeout(count, 1200);
  }
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') count(); });
  window.addEventListener('pageshow', event => { if (event.persisted) { sent = false; count(); } });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready, {once:true}); else ready();
})();
