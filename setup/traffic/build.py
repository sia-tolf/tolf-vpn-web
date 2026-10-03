#!/usr/bin/python3
from pathlib import Path

base = Path(__file__).resolve().parent
source = (base / 'install-moscow-receiver-template.py').read_text()
source = source.replace("'__TOLF_RECEIVER_PAYLOAD__'", repr((base / 'radius_accounting.py').read_text()))
compile(source, 'install-moscow-receiver.py', 'exec')
(base / 'install-moscow-receiver.py').write_text(source)
