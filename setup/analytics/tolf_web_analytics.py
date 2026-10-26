"""First-party, aggregate website statistics. No IPs, raw URLs or user agents on disk."""
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

ORIGIN = 'https://vpn.tolf.is'
RETENTION_DAYS = 90
HEADERS = {'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'}
PAGES = {'/', '/account/', '/auth/', '/billing/', '/connection/', '/quick/',
         '/help.html', '/contact.html', '/privacy.html', '/terms.html',
         '/measurement-check.html', '/anyconnect-setup.html', '/billing/price-preview.html'}
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
BOT = re.compile(r'bot\b|crawler|spider|headless|curl/|wget/|python-|monitor|uptime|facebookexternalhit|preview', re.I)


class Analytics:
    def __init__(self, main_db, path, auth, clock=time.time):
        self.main_db, self.path, self.auth, self.clock = main_db, str(path), auth, clock
        self.limit_lock = threading.Lock()
        self.limits = {}
        self.cleanup_at = 0
        with self.db() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS excluded_accounts(account_key TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS browsers(browser_key TEXT PRIMARY KEY,first_visit TEXT NOT NULL,first_seen REAL NOT NULL,last_seen REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS views(event_id TEXT PRIMARY KEY,at REAL NOT NULL,day TEXT NOT NULL,
              page TEXT NOT NULL,referrer TEXT NOT NULL,browser_key TEXT,visit_key TEXT,is_returning INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS views_at ON views(at);
            CREATE INDEX IF NOT EXISTS views_day ON views(day);
            ''')
            c.execute('INSERT OR IGNORE INTO meta VALUES(?,?)', ('started_at', str(self.clock())))
            c.execute('INSERT OR IGNORE INTO meta VALUES(?,?)', ('secret', secrets.token_hex(32)))
            self.secret = bytes.fromhex(c.execute("SELECT value FROM meta WHERE key='secret'").fetchone()[0])
            # Freeze the two known owner accounts, rather than inferring ownership from IPs.
            with closing(sqlite3.connect('file:' + self.main_db + '?mode=ro', uri=True)) as m:
                for number, name in [(9, 'user0_ipad'), (16, 'user0')]:
                    row = m.execute('SELECT account_id FROM managed_users WHERE number=? AND vpn_username=? AND deleted_at IS NULL', (number, name)).fetchone()
                    if row and row[0]:
                        c.execute('INSERT OR IGNORE INTO excluded_accounts VALUES(?)', (self.key('account', row[0]),))
        os.chmod(self.path, 0o600)

    @contextmanager
    def db(self):
        c = sqlite3.connect(self.path, timeout=5)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def key(self, kind, value):
        return hmac.new(self.secret, (kind + ':' + value).encode(), hashlib.sha256).hexdigest()

    def excluded(self, request):
        try:
            uid = self.auth(request)
        except HTTPException as e:
            if e.status_code == 401:
                return False
            raise
        with closing(sqlite3.connect('file:' + self.main_db + '?mode=ro', uri=True)) as c:
            if c.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (uid,)).fetchone():
                return True
        with self.db() as c:
            return bool(c.execute('SELECT 1 FROM excluded_accounts WHERE account_key=?', (self.key('account', uid),)).fetchone())

    def admin(self, request):
        uid = self.auth(request)
        with closing(sqlite3.connect('file:' + self.main_db + '?mode=ro', uri=True)) as c:
            if not c.execute('SELECT 1 FROM admin_roles WHERE user_id=?', (uid,)).fetchone():
                raise HTTPException(403, 'administrator_required')
        return uid

    def limited(self, request):
        now = int(self.clock() // 60)
        # This short-lived in-memory value is used only to limit abuse; never written to disk.
        address = request.client.host if request.client else 'unknown'
        try:
            if ipaddress.ip_address(address).is_loopback:
                address = request.headers.get('x-forwarded-for', address).split(',')[-1].strip()
        except ValueError:
            address = 'unknown'
        key = self.key('rate-' + str(now), address)
        with self.limit_lock:
            if self.limits.get('minute') != now:
                self.limits = {'minute': now, 'total': 0}
            if self.limits['total'] >= 1200 or self.limits.get(key, 0) >= 120:
                return True
            self.limits['total'] += 1
            self.limits[key] = self.limits.get(key, 0) + 1
        return False

    @staticmethod
    def clean_referrer(value):
        if not isinstance(value, str) or len(value) > 253:
            raise HTTPException(400, 'invalid_referrer')
        value = value.lower().rstrip('.')
        if not value or value == 'tolf.is' or value.endswith('.tolf.is'):
            return ''
        if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', value):
            return ''
        try:
            ipaddress.ip_address(value)
            return ''
        except ValueError:
            return value

    def record(self, request, payload):
        if request.headers.get('origin') != ORIGIN:
            raise HTTPException(403, 'origin_required')
        ua = request.headers.get('user-agent', '')
        if not ua or BOT.search(ua) or request.headers.get('dnt') == '1' or request.headers.get('sec-gpc') == '1':
            return {'status': 'ignored'}
        if self.excluded(request):
            return {'status': 'excluded', 'excluded': True}
        if self.limited(request):
            raise HTTPException(429, 'analytics_rate_limited')
        if not isinstance(payload, dict) or set(payload) - {'eventId', 'page', 'referrer', 'consent', 'browserId', 'visitId'}:
            raise HTTPException(400, 'invalid_event')
        event_id, page = payload.get('eventId'), payload.get('page')
        if not isinstance(event_id, str) or not UUID.fullmatch(event_id):
            raise HTTPException(400, 'invalid_event')
        if page == '/index.html':
            page = '/'
        if isinstance(page, str) and page.endswith('/index.html'):
            page = page[:-10]
        if not isinstance(page, str) or page not in PAGES:
            raise HTTPException(400, 'invalid_page')
        consent = payload.get('consent', False)
        if type(consent) is not bool:
            raise HTTPException(400, 'invalid_consent')
        browser = visit = None
        if consent:
            for field in ('browserId', 'visitId'):
                if not isinstance(payload.get(field), str) or not UUID.fullmatch(payload[field]):
                    raise HTTPException(400, 'invalid_identifier')
            browser, visit = self.key('browser', payload['browserId']), self.key('visit', payload['visitId'])
        elif payload.get('browserId') or payload.get('visitId'):
            raise HTTPException(400, 'consent_required')
        referrer = self.clean_referrer(payload.get('referrer', ''))
        now = self.clock()
        day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM views WHERE event_id=?', (event_id,)).fetchone():
                return {'status': 'ok'}
            returning = 0
            if browser:
                prior = c.execute('SELECT first_visit FROM browsers WHERE browser_key=?', (browser,)).fetchone()
                returning = int(prior is not None and prior['first_visit'] != visit)
                c.execute('INSERT INTO browsers VALUES(?,?,?,?) ON CONFLICT(browser_key) DO UPDATE SET last_seen=excluded.last_seen', (browser, visit, now, now))
            c.execute('INSERT INTO views VALUES(?,?,?,?,?,?,?,?)', (event_id, now, day, page, referrer, browser, visit, returning))
            if now >= self.cleanup_at:
                cutoff = now - RETENTION_DAYS * 86400
                c.execute('DELETE FROM views WHERE at<?', (cutoff,))
                c.execute('DELETE FROM browsers WHERE last_seen<?', (cutoff,))
                self.cleanup_at = now + 3600
        return {'status': 'ok'}

    def stats(self, request, days):
        self.admin(request)
        if days not in (1, 7, 30, 90):
            raise HTTPException(400, 'invalid_period')
        now = datetime.fromtimestamp(self.clock(), timezone.utc)
        start = datetime.combine(now.date() - timedelta(days=days - 1), datetime.min.time(), timezone.utc).timestamp()
        cutoff = max(start, self.clock() - RETENTION_DAYS * 86400)
        with self.db() as c:
            started = float(c.execute("SELECT value FROM meta WHERE key='started_at'").fetchone()[0])
            totals = dict(c.execute('SELECT COUNT(*) AS views,COUNT(DISTINCT visit_key) AS visits,COUNT(DISTINCT browser_key) AS browsers,COUNT(DISTINCT CASE WHEN is_returning=1 THEN browser_key END) AS returningBrowsers,COALESCE(SUM(browser_key IS NULL),0) AS unrecognisedViews,MAX(at) AS lastViewAt FROM views WHERE at>=?', (cutoff,)).fetchone())
            daily = [dict(r) for r in c.execute('SELECT day,COUNT(*) AS views,COUNT(DISTINCT visit_key) AS visits,COUNT(DISTINCT browser_key) AS browsers FROM views WHERE at>=? GROUP BY day ORDER BY day DESC', (cutoff,))]
            pages = [dict(r) for r in c.execute('SELECT page,COUNT(*) AS views FROM views WHERE at>=? GROUP BY page ORDER BY views DESC,page LIMIT 30', (cutoff,))]
            sources = [dict(r) for r in c.execute('SELECT referrer,COUNT(*) AS views FROM views WHERE at>=? GROUP BY referrer ORDER BY views DESC,referrer LIMIT 20', (cutoff,))]
        return {'startedAt': started, 'from': start, 'to': self.clock(), 'days': days, 'timezone': 'UTC', 'retentionDays': RETENTION_DAYS, 'totals': totals, 'daily': daily, 'pages': pages, 'sources': sources}


def install(app, context, path='/var/lib/tolf-api/web-analytics.db'):
    analytics = Analytics(context['DB'], path, context['authenticated_user_id'])
    app.state.web_analytics = analytics

    @app.post('/analytics/view')
    async def view(request: Request):
        if request.headers.get('origin') != ORIGIN:
            raise HTTPException(403, 'origin_required')
        body = bytearray()
        async for part in request.stream():
            body.extend(part)
            if len(body) > 2048:
                raise HTTPException(413, 'event_too_large')
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError):
            raise HTTPException(400, 'invalid_event')
        result = await run_in_threadpool(analytics.record, request, payload)
        return JSONResponse(result, headers=HEADERS)

    @app.get('/admin/analytics')
    def stats(request: Request, days: int = 7):
        return JSONResponse(analytics.stats(request, days), headers=HEADERS)
