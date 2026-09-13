"""TOLF Windows devices, independently owned by an authenticated account.
Initial native-Windows entry point: Riga, server-side split routing.
No credentials in the account database; existing Riga provisioning owns them.
"""
from contextlib import contextmanager
import hashlib
import html
import io
import json
import re
import secrets
import sqlite3
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, Response

VERSION = '1.0'
INSTALLER = Path(__file__).with_name('TOLF-Setup.exe')
CTX = None
TOKEN = re.compile(r'[A-Za-z0-9_-]{32}')
HEADERS = {'Cache-Control': 'private, no-store, max-age=0',
           'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'}
TEXT = {
 'en': ['Windows setup', 'Download Windows setup', 'Open this link on your Windows computer. Download the ZIP, extract all files, then run Install-TOLF.cmd. Open Windows Settings → Network & Internet → VPN to connect.', 'This package contains a VPN password. Delete the ZIP and extracted files after setup.', 'Back to TOLF VPN', 'Valid until', 'Riga entry point; Russian destinations through Moscow, other traffic through Riga. DNS is assigned by the VPN server.'],
 'ru': ['Настройка Windows', 'Скачать настройку Windows', 'Откройте ссылку на Windows-компьютере. Скачайте ZIP, извлеките все файлы и запустите Install-TOLF.cmd. Для подключения откройте Параметры Windows → Сеть и Интернет → VPN.', 'Пакет содержит пароль VPN. После настройки удалите ZIP и извлечённые файлы.', 'Назад в TOLF VPN', 'Действует до', 'Вход через Ригу: российские направления через Москву, остальные через Ригу. DNS назначает VPN-сервер.'],
 'lv': ['Windows iestatīšana', 'Lejupielādēt Windows iestatījumus', 'Atveriet saiti Windows datorā. Lejupielādējiet ZIP, izvelciet visus failus un palaidiet Install-TOLF.cmd. Lai izveidotu savienojumu, atveriet Windows iestatījumi → Tīkls un internets → VPN.', 'Pakotnē ir VPN parole. Pēc iestatīšanas izdzēsiet ZIP un izvilktos failus.', 'Atpakaļ uz TOLF VPN', 'Derīgs līdz', 'Ieeja caur Rīgu: Krievijas adreses caur Maskavu, pārējā datplūsma caur Rīgu. DNS piešķir VPN serveris.']
}

@contextmanager
def db():
    c = sqlite3.connect(CTX['DB'], timeout=30)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()


def initialize():
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS windows_devices (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL,
            username TEXT, state TEXT NOT NULL, created_at TEXT NOT NULL)''')
        c.execute('CREATE INDEX IF NOT EXISTS windows_devices_owner ON windows_devices(user_id)')


def now():
    return datetime.now(timezone.utc)


def identity(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, 'Invalid device ID')


def owned(user_id, device_id):
    with db() as c:
        row = c.execute('SELECT * FROM windows_devices WHERE user_id=? AND id=?',
                        (user_id, identity(device_id))).fetchone()
    if row is None:
        raise HTTPException(404, 'Windows device not found')
    if row['state'] == 'deleted':
        raise HTTPException(410, 'Windows device was deleted')
    return dict(row)


def public(row):
    return {k: row[k] for k in ('id', 'name', 'username', 'state', 'created_at')}


def invalidate(device_id):
    # Only this device's temporary Windows packages; Apple/Android untouched.
    directory = CTX['tolf_profiles'].PROFILE_DIR
    for path in directory.glob('*.json'):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if data.get('platform') == 'windows' and data.get('deviceId') == device_id and TOKEN.fullmatch(path.stem):
            path.with_suffix('.windows.zip').unlink(missing_ok=True)
            path.unlink(missing_ok=True)


def remove(user_id, device_id):
    row = owned(user_id, device_id)
    with db() as c:
        c.execute("UPDATE windows_devices SET state='deleting' WHERE id=? AND user_id=?", (row['id'], user_id))
    invalidate(row['id'])
    CTX['remove_provisioned_vpn'](row['id'], row['username'])
    CTX['provision_on_riga']('revoke-moscow', row['id'])
    with db() as c:
        c.execute("UPDATE windows_devices SET state='deleted' WHERE id=? AND user_id=?", (row['id'], user_id))


def delete_all(user_id):
    # Called under the same account-operation lock as the old account deletion.
    with db() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM windows_devices WHERE user_id=? AND state!='deleted'", (user_id,))]
    for device_id in ids:
        remove(user_id, device_id)


def language(payload):
    value = (payload or {}).get('language', 'en')
    if value not in TEXT:
        raise HTTPException(400, 'Invalid language')
    return value


def package(row, credentials, lang):
    expected = 'user_' + uuid.UUID(row['id']).hex
    username, password = credentials.get('username'), credentials.get('password')
    if username != expected or (row['username'] and row['username'] != username) or not CTX['tolf_profiles']._valid_secret(password):
        raise HTTPException(502, 'Invalid Windows credentials from VPN server')
    if credentials.get('server') != 'riga' or credentials.get('localId') != 'sr':
        raise HTTPException(502, 'Invalid Windows route from VPN server')
    settings = {'deviceId': row['id'], 'server': 'ikev2-riga.tolf.is',
                'username': username, 'password': password}
    output = io.BytesIO()
    template = Path(__file__).with_name('tolf-windows-install.ps1').read_text()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('connection.json', json.dumps(settings, ensure_ascii=True))
        archive.writestr('Install-TOLF.ps1', template.encode('utf-8-sig'))
        archive.writestr('Install-TOLF.cmd', '@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-TOLF.ps1"\r\nif errorlevel 1 echo TOLF setup failed. Read the error above.\r\npause\r\n')
        archive.writestr('README.txt', ('\n\n'.join([TEXT[lang][0], TEXT[lang][2], TEXT[lang][6], TEXT[lang][3]])).encode('utf-8-sig'))
    profiles = CTX['tolf_profiles']
    profiles.initialize()
    token = secrets.token_urlsafe(24)
    content = output.getvalue()
    metadata = {'platform': 'windows', 'deviceId': row['id'], 'name': row['name'],
                'username': username, 'language': lang, 'expiresAt': (now()+timedelta(hours=24)).isoformat(),
                'sha256': hashlib.sha256(content).hexdigest()}
    archive_path = profiles.PROFILE_DIR / (token + '.windows.zip')
    meta_path = profiles.PROFILE_DIR / (token + '.json')
    try:
        profiles._atomic_write(archive_path, content)
        profiles._atomic_write(meta_path, json.dumps(metadata).encode())
    except Exception:
        archive_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        raise
    return 'https://api.tolf.is/windows/p/' + token


def load(token):
    if not TOKEN.fullmatch(token):
        raise HTTPException(404, 'Windows package not found')
    directory = CTX['tolf_profiles'].PROFILE_DIR
    try:
        metadata = json.loads((directory / (token + '.json')).read_text())
        if metadata.get('platform') != 'windows':
            raise ValueError()
        expires = datetime.fromisoformat(metadata['expiresAt'])
    except (OSError, ValueError, KeyError):
        raise HTTPException(404, 'Windows package not found')
    if now() >= expires:
        raise HTTPException(410, 'Windows setup link expired')
    with db() as c:
        active = c.execute("SELECT id FROM windows_devices WHERE id=? AND state='active'", (metadata['deviceId'],)).fetchone()
    if not active:
        raise HTTPException(410, 'Windows device is not active')
    try:
        content = (directory / (token + '.windows.zip')).read_bytes()
    except OSError:
        raise HTTPException(404, 'Windows package not found')
    if hashlib.sha256(content).hexdigest() != metadata['sha256']:
        raise HTTPException(500, 'Windows package checksum mismatch')
    return metadata, content


def install(app, context):
    global CTX
    CTX = context
    app.router.add_event_handler('startup', initialize)

    @app.get('/windows/capabilities')
    def capabilities():
        return {'version': VERSION, 'servers': ['riga'], 'routing': 'sr', 'installerVersion': '1.2.0'}

    @app.get('/windows/devices')
    def devices(request: Request):
        user_id = CTX['authenticated_user_id'](request)
        with db() as c:
            rows = c.execute("SELECT * FROM windows_devices WHERE user_id=? AND state!='deleted' ORDER BY created_at,id", (user_id,)).fetchall()
        return Response(json.dumps({'devices': [public(r) for r in rows]}), media_type='application/json', headers=HEADERS)

    @app.post('/windows/devices')
    def create(request: Request, payload: dict):
        user_id = CTX['authenticated_user_id'](request)
        lang = language(payload)
        request_id = identity(payload.get('requestId'))
        name = payload.get('name', '')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 64 or any(ord(ch)<32 for ch in name):
            raise HTTPException(400, 'Enter a device name (1–64 characters)')
        # Stable across network retries, namespaced to the authenticated owner.
        device_id = str(uuid.uuid5(uuid.UUID(user_id), 'windows:' + request_id))
        with CTX['tolf_promos'].account_operation(CTX['DB'], user_id):
            with db() as c:
                existing = c.execute('SELECT id FROM windows_devices WHERE id=? AND user_id=?', (device_id, user_id)).fetchone()
                if not existing:
                    count = c.execute("SELECT count(*) FROM windows_devices WHERE user_id=? AND state!='deleted'", (user_id,)).fetchone()[0]
                    if count >= 20:
                        raise HTTPException(409, 'Windows device limit reached')
                    c.execute('INSERT INTO windows_devices VALUES (?,?,?,?,?,?)',
                              (device_id, user_id, name.strip(), None, 'provisioning', now().isoformat()))
            row = owned(user_id, device_id)
            if row['state'] == 'deleting':
                raise HTTPException(409, 'Device deletion is pending')
            CTX['provision_on_riga']('grant-moscow', device_id)
            credentials = CTX['provision_on_riga']('create', device_id, 'riga', 'sr')
            url = package(row, credentials, lang)
            with db() as c:
                c.execute("UPDATE windows_devices SET state='active',username=? WHERE id=? AND user_id=?", (credentials['username'], device_id, user_id))
            return {'device': public(owned(user_id, device_id)), 'profileUrl': url}

    @app.post('/windows/devices/{device_id}/profile')
    def profile(device_id: str, request: Request, payload: dict):
        user_id = CTX['authenticated_user_id'](request)
        lang = language(payload)
        with CTX['tolf_promos'].account_operation(CTX['DB'], user_id):
            row = owned(user_id, device_id)
            if row['state'] == 'deleting':
                raise HTTPException(409, 'Device deletion is pending')
            action = 'profile' if row['state'] == 'active' else 'create'
            if action == 'create':
                CTX['provision_on_riga']('grant-moscow', row['id'])
            credentials = CTX['provision_on_riga'](action, row['id'], 'riga', 'sr')
            url = package(row, credentials, lang)
            with db() as c:
                c.execute("UPDATE windows_devices SET state='active',username=? WHERE id=? AND user_id=?", (credentials['username'], row['id'], user_id))
            return {'profileUrl': url}

    @app.post('/windows/devices/{device_id}/delete')
    def delete(device_id: str, request: Request):
        user_id = CTX['authenticated_user_id'](request)
        with CTX['tolf_promos'].account_operation(CTX['DB'], user_id):
            # A repeated delete is idempotent, but ownership is always checked.
            try:
                remove(user_id, device_id)
            except HTTPException as exc:
                if exc.status_code != 410:
                    raise
        return {'status': 'ok'}

    @app.post('/windows/p/{token}/settings')
    def settings(token: str):
        metadata, content = load(token)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            config = json.loads(archive.read('connection.json'))
        if config.get('deviceId') != metadata['deviceId'] or config.get('username') != metadata['username']:
            raise HTTPException(500, 'Invalid Windows settings')
        return Response(json.dumps(config), media_type='application/json', headers=HEADERS)

    @app.get('/windows/p/{token}/download')
    def download(token: str):
        load(token)
        if not INSTALLER.is_file():
            raise HTTPException(503, 'Windows installer unavailable')
        return Response(INSTALLER.read_bytes(), media_type='application/octet-stream', headers={**HEADERS,
            'Content-Disposition': f'attachment; filename="TOLF-Setup-{token}.exe"'})

    @app.get('/windows/p/{token}')
    def page(token: str):
        metadata, _ = load(token)
        lang = metadata['language']
        labels = TEXT[lang]
        copy = {
            'en': ['Send to computer', 'Copy personal link', 'Personal setup link', 'Open this link on your Windows computer to set up TOLF VPN.', 'Install for Windows', 'Open the downloaded file and select “Set up and connect”.', 'Link copied', 'Copy the link from the field below.', 'Keep this personal link private.'],
            'ru': ['Отправить на компьютер', 'Скопировать ссылку', 'Персональная ссылка настройки', 'Откройте эту ссылку на компьютере Windows, чтобы настроить TOLF VPN.', 'Установить для Windows', 'Откройте скачанный файл и нажмите «Настроить и подключиться».', 'Ссылка скопирована', 'Скопируйте ссылку из поля ниже.', 'Не передавайте персональную ссылку посторонним.'],
            'lv': ['Nosūtīt uz datoru', 'Kopēt saiti', 'Personīgā iestatīšanas saite', 'Atveriet šo saiti Windows datorā, lai iestatītu TOLF VPN.', 'Instalēt Windows', 'Atveriet lejupielādēto failu un izvēlieties “Iestatīt un savienot”.', 'Saite nokopēta', 'Kopējiet saiti no zemāk redzamā lauka.', 'Nekopīgojiet personīgo saiti ar svešiniekiem.']
        }[lang]
        escape = html.escape
        url = 'https://api.tolf.is/windows/p/' + token
        expiry = datetime.fromisoformat(metadata['expiresAt']).strftime('%d.%m.%Y, %H:%M UTC')
        nonce = secrets.token_urlsafe(18)
        body = f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>TOLF — {escape(labels[0])}</title>
<style>:root{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light dark}}*{{box-sizing:border-box}}body{{max-width:660px;margin:32px auto;padding:24px;line-height:1.5}}a{{color:inherit}}h1{{font-size:28px}}.actions{{display:grid;gap:12px;margin:24px 0}}button,.download{{display:block;width:100%;text-align:center;border:1px solid #888;border-radius:12px;padding:14px;font:inherit;font-weight:600;text-decoration:none;background:transparent;color:inherit;cursor:pointer}}.primary{{background:#333;color:white;border-color:#333}}input{{width:100%;font:inherit;padding:12px;border:1px solid #aaa;border-radius:10px;background:transparent;color:inherit}}small,.note{{opacity:.7}}[hidden]{{display:none!important}}label{{display:block;margin:12px 0 6px}}</style></head><body><main><a href="https://vpn.tolf.is/">{escape(labels[4])}</a><h1>{escape(labels[0])}</h1><p>{escape(metadata['name'])}</p>
<p id="mobile-help">{escape(copy[3])}</p><p id="windows-help" hidden>{escape(copy[5])}</p><p>{escape(labels[6])}</p>
<div class="actions"><a id="download" class="download primary" href="/windows/p/{token}/download" hidden>{escape(copy[4])}</a><button id="send" class="primary" type="button">{escape(copy[0])}</button><button id="copy" type="button">{escape(copy[1])}</button></div>
<label for="personal-link">{escape(copy[2])}</label><input id="personal-link" readonly value="{escape(url)}" spellcheck="false" autocomplete="off"><p id="status" role="status" aria-live="polite"></p><p class="note">{escape(copy[8])}</p><small>{escape(labels[5])}: {escape(expiry)}</small></main>
<script nonce="{nonce}">
const url = document.getElementById('personal-link').value;
const status = document.getElementById('status');
const messages = {json.dumps(copy, ensure_ascii=True)};
const win = /Windows NT/i.test(navigator.userAgent);
document.getElementById('download').hidden = !win;
document.getElementById('windows-help').hidden = !win;
document.getElementById('mobile-help').hidden = win;
if (win) document.getElementById('send').classList.remove('primary');
async function copyLink() {{
 try {{ if (!navigator.clipboard) throw new Error(); await navigator.clipboard.writeText(url); status.textContent = messages[6]; }}
 catch {{ const field=document.getElementById('personal-link'); field.focus(); field.select(); status.textContent=messages[7]; }}
}}
document.getElementById('copy').addEventListener('click',copyLink);
document.getElementById('send').addEventListener('click',async()=>{{
 if (!navigator.share) {{ await copyLink(); return; }}
 try {{ await navigator.share({{title:'TOLF VPN — Windows',url}}); }}
 catch(e) {{ if(e.name!=='AbortError') await copyLink(); }}
}});
</script></body></html>'''
        return HTMLResponse(body, headers={**HEADERS, 'X-Frame-Options': 'DENY',
            'Content-Security-Policy': f"default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-{nonce}'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"})
