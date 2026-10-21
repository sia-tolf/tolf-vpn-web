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
    print("Ввод ключей Montonio Sandbox. Символы при вставке не отображаются.")
    print("Вставляйте по одному ключу, затем нажимайте Enter. Ctrl+C — отмена.")
    def read_key(label):
        while True:
            try:
                value = getpass.getpass(label + ": ").strip()
            except (EOFError, KeyboardInterrupt):
                raise SystemExit("\nВвод отменён. Файл не изменён.")
            if not value:
                print("Поле пустое. Вставьте ключ ещё раз; при скрытом вводе символов не видно.")
                continue
            if any(ord(c) < 32 or ord(c) == 127 for c in value):
                print("Вставлен перенос строки или управляющий символ. Скопируйте только сам ключ.")
                continue
            print("Ключ принят.")
            return value
    access = read_key("1. Sandbox Access Key")
    secret = read_key("2. Sandbox Secret Key")
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
