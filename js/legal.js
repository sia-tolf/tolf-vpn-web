(() => {
  'use strict';
  const langs = ['en', 'ru', 'lv'];
  const page = document.documentElement.dataset.legalPage;
  const url = new URL(location.href);
  const fixed = document.documentElement.dataset.legalStatic === 'true';
  let lang = document.documentElement.lang;
  if (!fixed) {
    lang = url.searchParams.get('lang');
    if (!langs.includes(lang)) {
      try { lang = localStorage.getItem('tolfLanguage'); } catch {}
    }
    if (!langs.includes(lang)) lang = (navigator.language || 'en').slice(0, 2);
    if (!langs.includes(lang)) lang = 'en';
    url.pathname = '/' + lang + '/' + page + '.html';
    url.searchParams.delete('lang');
    location.replace(url.href);
    return;
  }
  if (url.searchParams.has('lang')) {
    url.searchParams.delete('lang');
    history.replaceState(null, '', url.href);
  }
  try { localStorage.setItem('tolfLanguage', lang); } catch {}
  for (const link of document.querySelectorAll('[data-legal-select]')) {
    const target = new URL(link.href);
    target.search = url.search;
    target.hash = url.hash.replace(/-(en|ru|lv)$/, '-' + link.dataset.legalSelect);
    link.href = target.href;
  }
})();
