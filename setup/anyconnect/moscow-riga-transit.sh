#!/bin/sh
# Riga already chose Moscow for these packets; do not route them back to Riga.
set -eu
CURRENT="$(ip -4 rule show | awk '$1 == "8983:" { print }')"
if [ -n "$CURRENT" ]; then
    [ "$(printf '%s\n' "$CURRENT" | wc -l)" -eq 1 ] || {
        echo 'ERROR: duplicate rule priority 8983' >&2; exit 1;
    }
    printf '%s\n' "$CURRENT" | grep -Eq \
        '^8983:[[:space:]]+from 10\.19\.0\.0/24 iif gre4-riga_gre lookup main[[:space:]]*$' || {
        echo 'ERROR: rule priority 8983 belongs to another policy' >&2; exit 1;
    }
else
    ip -4 rule add priority 8983 from 10.19.0.0/24 iif gre4-riga_gre lookup main
fi
