def install(app, context):
    def reconcile():
        fd = os.open(directory / "reconcile.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            with closing(sqlite3.connect(db, timeout=30)) as con, con:
                con.execute("UPDATE oc_devices SET state='revoking',revoked_at=COALESCE(revoked_at,?) WHERE state IN ('pending','active') AND (expires_at<=? OR NOT EXISTS (SELECT 1 FROM users WHERE id=oc_devices.user_id))", (utc_now().isoformat(),utc_now().isoformat()))
                rows = con.execute("SELECT id,username FROM oc_devices WHERE state='revoking'").fetchall()
            if not rows:
                return
            published_crl(authority, directory, db)
            failed = False
            for device_id, username in rows:
                try:
                    node.revoke(username)
                except HTTPException:
                    failed = True
                    continue
                with closing(sqlite3.connect(db, timeout=30)) as con, con:
                    con.execute("UPDATE oc_devices SET state='revoked' WHERE id=? AND state='revoking'", (device_id,))
                    con.execute('DELETE FROM oc_policy_retries WHERE device_id=?', (device_id,))
            if failed:
                raise HTTPException(503, 'Ingress revocation pending')
        finally:
            os.close(fd)

    def reconcile_policies():
        pass

