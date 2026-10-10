#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v shortcuts >/dev/null || {
  echo "Apple Shortcuts CLI is required on macOS 12 or newer."
  exit 1
}
python3 shortcuts/build.py
mkdir -p shortcuts/signed
for name in "TOLF ON" "TOLF OFF"; do
  shortcuts sign --mode anyone     --input "shortcuts/unsigned/$name.shortcut"     --output "shortcuts/signed/$name.shortcut"
done
python3 - <<'PY'
from pathlib import Path
for name in ('TOLF ON', 'TOLF OFF'):
    path=Path('shortcuts/signed')/(name+'.shortcut')
    data=path.read_bytes()
    assert data.startswith(b'AEA1'), f'{name}: Apple signature missing'
    print(f'{name}: Apple-signed, {len(data)} bytes, ready for device testing')
PY
