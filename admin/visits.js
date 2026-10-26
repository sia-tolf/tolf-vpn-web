(() => {
  'use strict';
  const $ = id => document.getElementById(id), API = 'https://api.tolf.is', EXCLUDE = 'tolfAnalyticsExcluded';
  const copy = {
    ru:{title:'Посещения сайта',back:'Возврат',period:'Период',today:'Сегодня',week:'7 дней',month:'30 дней',quarter:'90 дней',refresh:'Обновить',views:'Просмотры',visits:'Визиты с меткой',browsers:'Браузеры с меткой',returning:'Повторные браузеры',limits:'Просмотры считаются без постоянной метки. Визиты и повторные браузеры распознаются только с разрешения посетителя. Это не число людей. Известные роботы, административные страницы и ваши известные аккаунты исключены. Блокировщики могут уменьшать показатели. Дни в таблице — по UTC.',excludeTitle:'Ваши посещения',excludeNote:'Аккаунты администратора и ваши два известных аккаунта не учитываются. Метка браузера исключает также посещения без входа в аккаунт.',exclude:'Не учитывать этот браузер',copyExclude:'Ссылка для другого моего браузера',daily:'По дням',pages:'Страницы',sources:'Источники переходов',date:'Дата (UTC)',page:'Страница',source:'Источник',direct:'Прямые и внутренние переходы',empty:'Посещений за этот период пока нет.',loading:'Загрузка…',denied:'Войдите на сайте под аккаунтом администратора и вернитесь сюда.',error:'Не удалось получить статистику. Попробуйте обновить.',started:'Учёт начат: ',last:'Последний учтённый просмотр: ',excluded:'Этот браузер не учитывается, в том числе после выхода из аккаунта.',notExcluded:'Метка браузера ещё не установлена.',storageError:'Браузер запрещает сохранение метки. Входы под вашим аккаунтом всё равно исключены.',copied:'Ссылка скопирована. Откройте её в другом своём браузере, чтобы исключить его посещения.',noCopy:'Ссылка: '},
    en:{title:'Website visits',back:'Back',period:'Period',today:'Today',week:'7 days',month:'30 days',quarter:'90 days',refresh:'Refresh',views:'Page views',visits:'Recognised visits',browsers:'Recognised browsers',returning:'Returning browsers',limits:'Page views do not require a persistent identifier. Visits and returning browsers are recognised only with permission. These are not counts of people. Known bots, admin pages and your known accounts are excluded. Blockers may reduce the counts. Daily rows use UTC.',excludeTitle:'Your visits',excludeNote:'Administrator accounts and your two known accounts are excluded. The browser marker also excludes visits after signing out.',exclude:'Exclude this browser',copyExclude:'Link for my other browser',daily:'By day',pages:'Pages',sources:'Referrers',date:'Date (UTC)',page:'Page',source:'Source',direct:'Direct and internal visits',empty:'No visits in this period yet.',loading:'Loading…',denied:'Sign in with an administrator account on the website, then return here.',error:'Could not load statistics. Try refreshing.',started:'Collection started: ',last:'Last counted page view: ',excluded:'This browser is excluded, including after sign-out.',notExcluded:'The browser marker has not been saved yet.',storageError:'This browser does not allow saving the marker. Your signed-in accounts are still excluded.',copied:'Link copied. Open it in another browser you own to exclude its visits.',noCopy:'Link: '},
    lv:{title:'Vietnes apmeklējumi',back:'Atpakaļ',period:'Periods',today:'Šodien',week:'7 dienas',month:'30 dienas',quarter:'90 dienas',refresh:'Atjaunināt',views:'Lapu skatījumi',visits:'Atpazīti apmeklējumi',browsers:'Atpazīti pārlūki',returning:'Atkārtoti pārlūki',limits:'Lapu skatījumiem nav vajadzīgs pastāvīgs identifikators. Apmeklējumus un atkārtotus pārlūkus atpazīstam tikai ar atļauju. Tas nav cilvēku skaits. Zināmie roboti, administrēšanas lapas un jūsu zināmie konti ir izslēgti. Bloķētāji var samazināt rādītājus. Dienu tabulā izmantots UTC.',excludeTitle:'Jūsu apmeklējumi',excludeNote:'Administratoru konti un jūsu divi zināmie konti netiek ieskaitīti. Pārlūka atzīme izslēdz arī apmeklējumus pēc izrakstīšanās.',exclude:'Neieskaitīt šo pārlūku',copyExclude:'Saite manam citam pārlūkam',daily:'Pa dienām',pages:'Lapas',sources:'Pāreju avoti',date:'Datums (UTC)',page:'Lapa',source:'Avots',direct:'Tiešie un iekšējie apmeklējumi',empty:'Šajā periodā vēl nav apmeklējumu.',loading:'Ielāde…',denied:'Vietnē pierakstieties ar administratora kontu un atgriezieties šeit.',error:'Neizdevās ielādēt statistiku. Mēģiniet atjaunināt.',started:'Uzskaite sākta: ',last:'Pēdējais ieskaitītais skatījums: ',excluded:'Šis pārlūks netiek ieskaitīts arī pēc izrakstīšanās.',notExcluded:'Pārlūka atzīme vēl nav saglabāta.',storageError:'Pārlūks neļauj saglabāt atzīmi. Jūsu kontu apmeklējumi joprojām ir izslēgti.',copied:'Saite nokopēta. Atveriet to citā savā pārlūkā, lai izslēgtu tā apmeklējumus.',noCopy:'Saite: '}
  };
Object.assign(copy.ru,{"trialsTitle":"Пробные регистрации","trialAccounts":"действующих аккаунтов с пробной регистрацией","trialsNote":"Всего по базе аккаунтов, независимо от выбранного периода просмотров. Отметка появляется только после явного оформления и сохраняется после покупки трафика.","trialAccountsLink":"Открыть список"});
Object.assign(copy.en,{"trialsTitle":"Trial registrations","trialAccounts":"active accounts with a trial registration","trialsNote":"Account database total, independent of the page-view period. Only explicit registrations are marked; the mark stays after a traffic purchase.","trialAccountsLink":"Open accounts"});
Object.assign(copy.lv,{"trialsTitle":"Izmēģinājuma reģistrācijas","trialAccounts":"aktīvi konti ar izmēģinājuma reģistrāciju","trialsNote":"Kopā kontu datubāzē neatkarīgi no skatījumu perioda. Atzīmi saņem tikai apzināti noformētas reģistrācijas; tā saglabājas pēc datu iegādes.","trialAccountsLink":"Atvērt kontu sarakstu"});
  let lang = new URL(location.href).searchParams.get('lang'), data = null, trialData = null, generation = 0;
  if (!copy[lang]) { try { lang = localStorage.getItem('tolfLanguage'); } catch {} }
  if (!copy[lang]) lang = /^ru/i.test(navigator.language) ? 'ru' : /^lv/i.test(navigator.language) ? 'lv' : 'en';
  const t = key => copy[lang][key], number = value => new Intl.NumberFormat(lang).format(value || 0);
  function excluded() { try { return localStorage.getItem(EXCLUDE) === '1'; } catch { return false; } }
  function mark() { try { localStorage.setItem(EXCLUDE,'1'); localStorage.removeItem('tolfAnalyticsBrowser'); } catch {} showExclusion(); }
  function showExclusion() { $('excludedStatus').textContent = t(excluded() ? 'excluded' : 'notExcluded'); $('exclude').hidden = excluded(); }
  function language() {
    document.documentElement.lang = lang; document.title = t('title') + ' — TOLF';
    document.querySelectorAll('[data-copy]').forEach(el => { el.textContent = t(el.dataset.copy); });
    document.querySelectorAll('[data-language]').forEach(el => el.setAttribute('aria-pressed',String(el.dataset.language === lang)));
    showExclusion(); if (data) render();
  }
  function table(target, headers, rows) {
    target.replaceChildren();
    if (!rows.length) { target.textContent = t('empty'); return; }
    const el = document.createElement('table'), head = document.createElement('thead'), hr = document.createElement('tr'), body = document.createElement('tbody');
    for (const value of headers) { const th = document.createElement('th'); th.scope = 'col'; th.textContent = value; hr.appendChild(th); }
    head.appendChild(hr);
    for (const row of rows) { const tr = document.createElement('tr'); for (const value of row) { const td = document.createElement('td'); td.textContent = value; tr.appendChild(td); } body.appendChild(tr); }
    el.append(head,body); target.appendChild(el);
  }
  function render() {
    $('trialCount').textContent = number(trialData?.activeTrialAccounts);
    $('trialAccountsLink').href = '/admin/?tab=users&trial=only&lang=' + lang;
    $('views').textContent = number(data.totals.views); $('visits').textContent = number(data.totals.visits); $('browsers').textContent = number(data.totals.browsers); $('returning').textContent = number(data.totals.returningBrowsers);
    $('started').textContent = t('started') + new Date(data.startedAt * 1000).toLocaleString(lang);
    $('latest').textContent = data.totals.lastViewAt ? t('last') + new Date(data.totals.lastViewAt * 1000).toLocaleString(lang) : t('empty');
    table($('dailyTable'),[t('date'),t('views'),t('browsers')],data.daily.map(r => [r.day,number(r.views),number(r.browsers)]));
    table($('pagesTable'),[t('page'),t('views')],data.pages.map(r => [r.page,number(r.views)]));
    table($('sourcesTable'),[t('source'),t('views')],data.sources.map(r => [r.referrer || t('direct'),number(r.views)]));
    const chart = $('dailyChart'), days = new Map(data.daily.map(r => [r.day,r.views])), counts = [];
    for (let i = 0; i < data.days; i++) { const day = new Date((data.from + i * 86400) * 1000).toISOString().slice(0,10); counts.push([day,days.get(day) || 0]); }
    chart.replaceChildren(); const maximum = Math.max(1,...counts.map(x => x[1]));
    for (const [day,value] of counts) { const bar = document.createElement('div'); bar.style.height = Math.max(1,value / maximum * 100) + '%'; bar.title = day + ': ' + number(value); chart.appendChild(bar); }
    chart.setAttribute('aria-label', t('daily') + ': ' + counts.map(x => x.join(' — ')).join(', ')); chart.hidden = !data.totals.views;
  }
  async function load() {
    const version = ++generation, controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 10000);
    $('message').textContent = t('loading'); $('refresh').disabled = true;
    try {
      const [response, trialsResponse] = await Promise.all([fetch(API + '/admin/analytics?days=' + $('period').value,{credentials:'include',cache:'no-store',signal:controller.signal}),fetch(API + '/admin/trial-registrations',{credentials:'include',cache:'no-store',signal:controller.signal})]);
      if (version !== generation) return;
      if (!response.ok) { const error = new Error(); error.status = response.status; throw error; }
      if (!trialsResponse.ok) { const error = new Error(); error.status = trialsResponse.status; throw error; }
      const [next, trials] = await Promise.all([response.json(),trialsResponse.json()]); if (version !== generation) return;
      data = next; trialData = trials; mark(); $('workspace').hidden = false; $('message').textContent = ''; render();
    } catch (error) { if (version === generation) { $('message').textContent = t([401,403].includes(error.status) ? 'denied' : 'error'); if ([401,403].includes(error.status)) $('workspace').hidden = true; } }
    finally { clearTimeout(timeout); if (version === generation) $('refresh').disabled = false; }
  }
  $('exclude').addEventListener('click',() => { mark(); if (!excluded()) $('excludedStatus').textContent = t('storageError'); });
  $('copyExclude').addEventListener('click',async () => { const link = 'https://vpn.tolf.is/?analytics=exclude'; try { await navigator.clipboard.writeText(link); $('copied').textContent = t('copied'); } catch { $('copied').textContent = t('noCopy') + link; } });
  $('refresh').addEventListener('click',load); $('period').addEventListener('change',load);
  document.querySelectorAll('[data-language]').forEach(el => el.addEventListener('click',() => { lang = el.dataset.language; try { localStorage.setItem('tolfLanguage',lang); } catch {} language(); }));
  language(); load();
})();

