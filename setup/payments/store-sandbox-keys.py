#!/usr/bin/env python3
"""Store merchant-supplied sandbox keys locally; never enables payments."""
import getpass
import grp
import json
import os
from pathlib import Path
import tempfile

def main():
    if os.geteuid() != 0:
        raise SystemExit("Run as root on the UK server.")
    access = getpass.getpass("Montonio Sandbox Access Key (hidden): ").strip()
    secret = getpass.getpass("Montonio Sandbox Secret Key (hidden): ").strip()
    if not access or not secret or any(c in access+secret for c in "\r\n\x00"):
        raise SystemExit("Both keys are required; no file was changed.")
    folder=Path("/etc/tolf-payments")
    folder.mkdir(mode=0o750,exist_ok=True)
    group=grp.getgrnam("tolfa").gr_gid
    os.chown(folder,0,group)
    os.chmod(folder,0o750)
    fd,name=tempfile.mkstemp(prefix=".sandbox-",dir=folder)
    try:
        os.fchmod(fd,0o640)
        os.fchown(fd,0,group)
        with os.fdopen(fd,"w") as f:
            json.dump({"environment":"sandbox","apiBase":"https://sandbox-stargate.montonio.com/api","accessKey":access,"secretKey":secret},f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name,folder/"montonio-sandbox.json")
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print("Sandbox keys saved. Real payments remain disabled. No keys were displayed.")

if __name__=="__main__":
    main()
