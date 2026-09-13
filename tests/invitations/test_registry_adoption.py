import contextlib
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from fastapi import HTTPException

spec=importlib.util.spec_from_file_location("fix", "setup/invitations/fix-registry-adoption.py")
fix=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.con=sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        self.con.executescript("""
        CREATE TABLE managed_users(number INTEGER PRIMARY KEY,account_id TEXT UNIQUE,vpn_username TEXT UNIQUE,created_at TEXT,source TEXT,vpn_active INTEGER,deleted_at TEXT,vpn_created_at TEXT);
        CREATE TABLE vpn_access(user_id TEXT PRIMARY KEY,vpn_username TEXT UNIQUE,created_at TEXT,server TEXT);
        CREATE TRIGGER managed_users_after_vpn_insert AFTER INSERT ON vpn_access BEGIN
        UPDATE managed_users SET vpn_username=NEW.vpn_username,vpn_created_at=NEW.created_at,vpn_active=1 WHERE account_id=NEW.user_id;
        END;
        INSERT INTO managed_users VALUES(11,NULL,'manual','old','legacy',1,NULL,'old');
        INSERT INTO managed_users VALUES(23,'account',NULL,'new','site',0,NULL,NULL);
        """)
        self.ns={"HTTPException":HTTPException,"CTX":{"utc_iso":lambda x:x,"utc_now":lambda:"now"}}
        exec(fix.HELPER,self.ns)
    def adopt(self):
        self.ns["reconcile_managed_user"](self.con,"account","manual")
    def test_original_number_and_login_preserved(self):
        with self.con:
            self.con.execute("BEGIN IMMEDIATE")
            self.adopt()
            self.con.execute("INSERT INTO vpn_access VALUES('account','manual','now','riga')")
        self.assertEqual(self.con.execute("SELECT number,account_id,vpn_username,source FROM managed_users WHERE number=11").fetchone(),(11,"account","manual","legacy"))
        self.assertEqual(self.con.execute("SELECT account_id,deleted_at FROM managed_users WHERE number=23").fetchone(),(None,"now"))
        self.adopt()
    def test_other_owner_never_reassigned(self):
        self.con.execute("UPDATE managed_users SET account_id='other' WHERE number=11")
        with self.assertRaises(HTTPException): self.adopt()
        self.assertEqual(self.con.execute("SELECT account_id FROM managed_users WHERE number=11").fetchone()[0],"other")
    def test_transaction_rollback(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.con:
                self.con.execute("BEGIN IMMEDIATE")
                self.adopt()
                self.con.execute("INSERT INTO vpn_access VALUES('account','manual','now','riga')")
                self.con.execute("INSERT INTO vpn_access VALUES('account','other','now','riga')")
        self.assertEqual(self.con.execute("SELECT account_id FROM managed_users WHERE number=11").fetchone()[0],None)
        self.assertEqual(self.con.execute("SELECT account_id FROM managed_users WHERE number=23").fetchone()[0],"account")
    def test_london_source_patch(self):
        source=Path("setup/invitations/tolf_invitations.py").read_text()
        changed=fix.patch(source)
        self.assertEqual(fix.patch(changed),changed)
        compile(changed,"patched","exec")
    def test_riga_expired_claim_retry(self):
        import ast, hashlib, hmac, re, time
        source=fix.patch_riga(Path("setup/invitations/tolf_invite_riga.py").read_text())
        tree=ast.parse(source)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="claim")
        class Rejected(Exception): pass
        ns={"account_id":lambda x:None,"TOKEN":re.compile("[a-z]{43}"),"hashlib":hashlib,"time":time,
            "credential_exists":lambda x:None,"PROTECTED":set(),"Rejected":Rejected,
            "hmac":hmac,"proof_digest":lambda u,p:p,"password_proof":lambda u:"proof"}
        exec(compile(ast.Module(body=[node],type_ignores=[]),"claim","exec"),ns)
        con=sqlite3.connect(":memory:")
        self.addCleanup(con.close)
        con.executescript("CREATE TABLE invitations(digest,username,expires,claimed_by,revoked,proof); CREATE TABLE bindings(account,username,created);")
        token="a"*43
        con.execute("INSERT INTO invitations VALUES(?,?,?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),"manual",0,"account",0,"proof"))
        con.execute("INSERT INTO bindings VALUES('account','manual',0)")
        self.assertEqual(ns["claim"](con,"account",token)["username"],"manual")
        with self.assertRaises(Rejected): ns["claim"](con,"other",token)
        con.execute("UPDATE invitations SET claimed_by=NULL")
        with self.assertRaises(Rejected): ns["claim"](con,"account",token)

if __name__=="__main__": unittest.main()
