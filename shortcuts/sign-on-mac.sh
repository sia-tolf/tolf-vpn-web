#!/bin/sh
set -eu
source_path="${1:?Usage: sign-on-mac.sh /path/to/working-on.shortcut}"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
command -v shortcuts >/dev/null
python3 "$script_dir/build.py" --source "$source_path"
mkdir -p "$script_dir/signed"
for name in "TOLF ON" "TOLF OFF"; do
  shortcuts sign --mode anyone --input "$script_dir/unsigned/$name.shortcut" --output "$script_dir/signed/$name.shortcut"
done
