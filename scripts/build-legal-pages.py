"""Generate static language versions from the existing, unchanged legal copy."""
from pathlib import Path
import re
from public_page_shell import document
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LANGS = ('en', 'ru', 'lv')
BASE = 'https://vpn.tolf.is'
DESCRIPTIONS = {
    'privacy': {'en':'TOLF privacy and personal data processing.', 'ru':'Конфиденциальность и обработка персональных данных TOLF.', 'lv':'TOLF privātums un personas datu apstrāde.'},
    'contact': {'en': 'Company details and support contacts for SIA Tolf, provider of TOLF VPN and SmartDNS.', 'ru': 'Реквизиты SIA Tolf и контакты поддержки TOLF VPN и SmartDNS.', 'lv': 'SIA Tolf rekvizīti un TOLF VPN un SmartDNS atbalsta kontaktinformācija.'},
    'terms': {'en': 'TOLF service terms: VPN and SmartDNS, traffic accounting, payments, refunds and support.', 'ru': 'Условия TOLF: VPN и SmartDNS, учёт трафика, оплата, возврат и поддержка.', 'lv': 'TOLF pakalpojuma noteikumi: VPN un SmartDNS, datu uzskaite, maksājumi, atmaksa un atbalsts.'},
}

def build(page, lang, alias=False):
    html = (ROOT / 'templates' / f'{page}.html').read_text()
    html = re.sub(r'<html lang="en">', f'<html lang="{lang}" data-legal-page="{page}" data-legal-static="{str(not alias).lower()}">', html, count=1)
    for tag in ('article', 'span'):
        html = re.sub(rf'<{tag}\b[^>]*data-legal-lang="(en|ru|lv)"[^>]*>.*?</{tag}>', lambda m: m[0] if m[1] == lang else '', html, flags=re.S)
    title = re.search(r'<h1>(.*?)</h1>', html)[1]
    canonical = f'{BASE}/{lang}/{page}.html'
    meta = f'<title>{title} — TOLF</title><meta name="description" content="{DESCRIPTIONS[page][lang]}"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}">'
    for alt in (*LANGS, 'x-default'):
        target = 'en' if alt == 'x-default' else alt
        meta += f'<link rel="alternate" hreflang="{alt}" href="{BASE}/{target}/{page}.html">'
    html = re.sub(r'<title>.*?</title>', lambda _: meta, html, count=1)
    html = re.sub(r'<button\b[^>]*data-legal-select="(en|ru|lv)"[^>]*>(.*?)</button>', lambda m: f'<a data-legal-select="{m[1]}" lang="{m[1]}" href="/{m[1]}/{page}.html"' + (' aria-current="page"' if m[1] == lang else '') + f'>{m[2]}</a>', html)
    def absolute(m):
        attr, value = m.groups()
        if not value.startswith(('/', 'https:', 'http:', 'mailto:', 'tel:', '#')):
            value = '/' + value.removeprefix('./')
        if attr == 'href' and value in ('/contact.html', '/terms.html'):
            value = f'/{lang}{value}'
        elif attr == 'href' and value == '/':
            value = f'/{lang}/'
        elif attr == 'href' and value in ('/privacy.html', '/billing/'):
            value += '?lang=' + lang
        return f'{attr}="{value}"'
    html = re.sub(r'(href|src)="([^"]*)"', absolute, html)
    html = html.replace('/js/legal.js?v=20261021', '/js/legal.js?v=20261118-static').replace('/css/legal.css?v=20261021', '/css/legal.css?v=20261118-static')
    dest = ROOT / (f'{page}.html' if alias else f'{lang}/{page}.html')
    dest.parent.mkdir(exist_ok=True)
    article = re.search(r'<article\b.*?</article>', html, re.S)[0]
    urls = {l: f'{BASE}/{l}/{page}.html' for l in LANGS}
    extra = '<script defer src="/js/legal.js?v=20261118-static"></script><link rel="stylesheet" href="/css/visits.css?v=20261026-2"><script defer src="/js/visits.js?v=20261026-2"></script>'
    attrs = f'data-legal-page="{page}" data-legal-static="{str(not alias).lower()}"'
    dest.write_text(document(lang, meta, article, urls, attrs, extra))

for page in DESCRIPTIONS:
    for lang in LANGS:
        build(page, lang)
    build(page, 'en', alias=True)

ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
xhtml = 'http://www.w3.org/1999/xhtml'
ET.register_namespace('', ns)
ET.register_namespace('xhtml', xhtml)
tree = ET.parse(ROOT / 'sitemap.xml')
root = tree.getroot()
for url in list(root):
    loc = url.find(f'{{{ns}}}loc').text
    if re.search(r'/(?:contact|terms|privacy)\.html$', loc) or re.search(r'/(?:en|ru|lv)/(?:contact|terms|privacy)\.html$', loc):
        root.remove(url)
for page in DESCRIPTIONS:
    for lang in LANGS:
        url = ET.SubElement(root, f'{{{ns}}}url')
        ET.SubElement(url, f'{{{ns}}}loc').text = f'{BASE}/{lang}/{page}.html'
        for alt in (*LANGS, 'x-default'):
            target = 'en' if alt == 'x-default' else alt
            ET.SubElement(url, f'{{{xhtml}}}link', rel='alternate', hreflang=alt, href=f'{BASE}/{target}/{page}.html')
ET.indent(tree, space='  ')
tree.write(ROOT / 'sitemap.xml', encoding='UTF-8', xml_declaration=True)
