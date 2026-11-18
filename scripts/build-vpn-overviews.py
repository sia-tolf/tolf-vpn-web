from pathlib import Path
import re
from public_page_shell import document
ROOT=Path(__file__).resolve().parents[1]
for lang in ('en','ru','lv'):
 source=(ROOT/'templates'/f'vpn-{lang}.html').read_text()
 head=re.search(r'<head>(.*?)</head>',source,re.S)[1]
 head=re.sub(r'<link[^>]*rel="stylesheet"[^>]*>','',head)
 head=re.sub(r'<meta[^>]*(?:charset=|name="viewport")[^>]*>','',head)
 content=re.search(r'<article>(.*?)</article>',source,re.S)[1]
 content=content.replace(f'/privacy.html?lang={lang}',f'/{lang}/privacy.html')
 urls={l:f'https://vpn.tolf.is/{l}/' for l in ('en','ru','lv')}
 (ROOT/lang/'index.html').write_text(document(lang,head,content,urls))
