import asyncio
import importlib.util
import json
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('analytics', ROOT / 'setup/analytics/tolf_web_analytics.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StatisticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.main = str(Path(self.temp.name) / 'main.db')
        self.path = str(Path(self.temp.name) / 'stats.db')
        self.now = 1793020000.0
        with sqlite3.connect(self.main) as c:
            c.executescript('CREATE TABLE managed_users(number INTEGER,account_id TEXT,vpn_username TEXT,deleted_at TEXT); CREATE TABLE admin_roles(user_id TEXT);')
            c.executemany('INSERT INTO managed_users VALUES(?,?,?,NULL)', [(9,'owner','user0_ipad'),(16,'phone','user0'),(20,'reader','reader')])
            c.execute('INSERT INTO admin_roles VALUES(?)', ('owner',))
        self.app = FastAPI()
        def auth(request):
            value = request.headers.get('x-fixture-user')
            if not value:
                raise HTTPException(401, 'not_authenticated')
            return value
        module.install(self.app, {'DB':self.main, 'authenticated_user_id':auth}, self.path)
        self.a = self.app.state.web_analytics
        self.a.clock = lambda: self.now

    def tearDown(self):
        self.temp.cleanup()

    def request(self, user=None, origin=module.ORIGIN, headers=None, body=b'{}'):
        raw = {'origin':origin,'user-agent':'Mozilla/5.0 Safari/605.1.15'}
        if user:
            raw['x-fixture-user'] = user
        raw.update(headers or {})
        async def receive():
            return {'type':'http.request','body':body,'more_body':False}
        return Request({'type':'http','method':'POST','path':'/analytics/view','headers':[(k.encode(),v.encode()) for k,v in raw.items()],'client':('203.0.113.11',1234),'scheme':'https','server':('api.tolf.is',443),'query_string':b''},receive)

    def event(self, **kwargs):
        return {'eventId':str(uuid.uuid4()),'page':'/billing/','referrer':'search.example',**kwargs}

    def stats(self):
        return self.a.stats(self.request('owner'),7)

    def assert_status(self, status, fn):
        with self.assertRaises(HTTPException) as raised:
            fn()
        self.assertEqual(raised.exception.status_code,status)

    def test_counts_and_returning_browsers_without_double_counting(self):
        browser, visit = str(uuid.uuid4()), str(uuid.uuid4())
        first = self.event(consent=True,browserId=browser,visitId=visit)
        self.a.record(self.request(),first)
        self.a.record(self.request(),first)
        self.a.record(self.request(),self.event(consent=True,browserId=browser,visitId=visit))
        self.assertEqual(self.stats()['totals']['returningBrowsers'],0)
        self.now += 1900
        self.a.record(self.request(),self.event(consent=True,browserId=browser,visitId=str(uuid.uuid4())))
        totals = self.stats()['totals']
        self.assertEqual((totals['views'],totals['browsers'],totals['visits'],totals['returningBrowsers']),(3,1,2,1))
        with sqlite3.connect(self.path) as c:
            stored = json.dumps(c.execute('SELECT * FROM views').fetchall())
        for private in (browser,visit,'203.0.113.11','Safari','owner'):
            self.assertNotIn(private,stored)

    def test_anonymous_views_do_not_create_browser_or_account_identifiers(self):
        self.a.record(self.request('reader'), self.event())
        self.a.record(self.request(), self.event(page='/index.html',referrer='vpn.tolf.is'))
        totals = self.stats()['totals']
        self.assertEqual((totals['views'],totals['browsers'],totals['visits'],totals['unrecognisedViews']),(2,0,0,2))
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM browsers').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT referrer FROM views WHERE page=?',('/',)).fetchone()[0],'')

    def test_guards_and_owner_exclusion(self):
        for user in ('owner','phone'):
            self.assertEqual(self.a.record(self.request(user), self.event())['status'],'excluded')
        for headers in ({'user-agent':'Googlebot/2.1'},{'dnt':'1'},{'sec-gpc':'1'}):
            self.assertEqual(self.a.record(self.request(headers=headers),self.event())['status'],'ignored')
        self.assertEqual(self.stats()['totals']['views'],0)
        self.assert_status(403,lambda:self.a.record(self.request(origin='https://evil.example'),self.event()))
        self.assert_status(401,lambda:self.a.stats(self.request(),7))
        self.assert_status(403,lambda:self.a.stats(self.request('reader'),7))
        self.assert_status(400,lambda:self.a.stats(self.request('owner'),100000))

    def test_sensitive_paths_queries_and_identifiers_are_rejected(self):
        for changed in ({'page':'/billing/?token=SECRET'},{'page':'/admin/'},{'page':'/oc/import/SECRET'}, {'page':[]}, {'browserId':str(uuid.uuid4())},{'eventId':'anything'},{'consent':'true'},{'consent':True,'browserId':'bad','visitId':str(uuid.uuid4())},{'token':'SECRET'}):
            self.assert_status(400,lambda changed=changed:self.a.record(self.request(),self.event(**changed)))
        self.assertEqual(self.stats()['totals']['views'],0)

    def test_retention_and_read_only_admin_endpoint(self):
        self.a.record(self.request(),self.event())
        self.now += 91 * 86400
        self.a.record(self.request(),self.event())
        self.assertEqual(self.stats()['totals']['views'],1)
        with sqlite3.connect(self.path) as c:
            before = c.execute('SELECT COUNT(*) FROM views').fetchone()[0]
            self.assertEqual(before,1)
        self.stats()
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM views').fetchone()[0],before)
        self.assertEqual(Path(self.path).stat().st_mode & 0o777,0o600)

    def test_http_routes_body_limit_and_no_store(self):
        endpoint = next(r.endpoint for r in self.app.routes if r.path == '/analytics/view')
        result = asyncio.run(endpoint(self.request(body=json.dumps(self.event()).encode())))
        self.assertEqual(result.status_code,200)
        self.assertIn('no-store',result.headers['cache-control'])
        self.assert_status(413,lambda:asyncio.run(endpoint(self.request(body=b'x'*2049))))
        self.assert_status(400,lambda:asyncio.run(endpoint(self.request(body=b'not json'))))


if __name__ == '__main__':
    unittest.main(verbosity=2)
