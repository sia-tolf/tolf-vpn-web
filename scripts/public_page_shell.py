from html import escape

LANGS = ('en', 'ru', 'lv')
LABELS = {
 'en': ('Back', 'Language', 'About TOLF VPN', 'Privacy', 'Terms of service', 'Company and contacts', 'Sitemap'),
 'ru': ('Возврат', 'Язык', 'О TOLF VPN', 'Конфиденциальность', 'Условия сервиса', 'Компания и контакты', 'Карта сайта'),
 'lv': ('Atpakaļ', 'Valoda', 'Par TOLF VPN', 'Privātums', 'Pakalpojuma noteikumi', 'Uzņēmums un kontakti', 'Vietnes karte'),
}

def header(lang, urls):
 c=LABELS[lang]
 switches=''.join(f'<a href="{escape(urls[l], quote=True)}" lang="{l}" hreflang="{l}" data-legal-select="{l}"'+(' aria-current="page"' if l==lang else '')+f'>{l.upper()}</a>' for l in LANGS)
 return f'<header class="public-header"><a class="public-return" href="https://tolf.is/{lang}/"><img src="https://tolf.is/tolf-logo-star.svg" width="28" height="28" alt="" aria-hidden="true"><span class="public-wordmark">TOLF</span><span class="public-arrow" aria-hidden="true">←</span><span>{c[0]}</span></a><nav class="public-language" aria-label="{c[1]}">{switches}</nav></header>'

def footer(lang):
 c=LABELS[lang]
 urls=[f'https://vpn.tolf.is/{lang}/',f'https://vpn.tolf.is/{lang}/privacy.html',f'https://vpn.tolf.is/{lang}/terms.html',f'https://vpn.tolf.is/{lang}/contact.html',f'https://tolf.is/{lang}/sitemap.html']
 return '<footer class="public-footer">'+''.join(f'<a href="{u}">{label}</a>' for u,label in zip(urls,c[2:]))+'</footer>'

def document(lang, head, content, urls, attributes='', extra='', *, show_footer=True):
 footer_html = footer(lang) if show_footer else ''
 return f'<!doctype html>\n<html lang="{lang}" {attributes}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">{head}<link rel="stylesheet" href="/public-page.css?v=20261118-unified"></head><body class="public-page"><div class="public-shell">{header(lang,urls)}<main class="public-content">{content}</main>{footer_html}</div>{extra}</body></html>\n'
