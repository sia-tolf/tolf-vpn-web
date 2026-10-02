#!/bin/sh
# Public trust only. All signing and device state remain on UK.
set -eu
TOLF_DIR="${TOLF_OC_DIRECTORY:-/etc/ocserv-moscow}"
TOLF_SOCKET="${TOLF_OC_SOCKET:-/var/run/occtl-moscow.socket}"
TOLF_CA="$TOLF_DIR/uk-client-ca.pem"
TOLF_CRL="$TOLF_DIR/uk-client-ca.crl.pem"
TOLF_LOCK="${TOLF_OC_LOCK_DIRECTORY:-/tmp/tolf-oc-crl-sync.lock}"
TOLF_LAST_SYNC="${TOLF_OC_LAST_SYNC:-/tmp/tolf-oc-crl-last-sync}"

if ! mkdir "$TOLF_LOCK" 2>/dev/null; then
    echo "CRL synchronization is already running" >&2
    exit 1
fi
trap 'rm -rf "$TOLF_LOCK"' EXIT
trap 'exit 1' HUP INT TERM
chmod 700 "$TOLF_LOCK"

openssl x509 -in "$TOLF_CA" -outform DER -out "$TOLF_LOCK/ca.der"
TOLF_ACTUAL="$(sha256sum "$TOLF_LOCK/ca.der" | awk '{print $1}')"
test "$TOLF_ACTUAL" = "$(cat "$TOLF_DIR/uk-client-ca.sha256")"

curl -fsS --connect-timeout 10 --max-time 30 --max-filesize 1048576 \
    https://api.tolf.is/oc/access/crl.pem -o "$TOLF_LOCK/new.pem"
# This checks issuer, signature, CA validity and CRL last/next update times.
openssl verify -CAfile "$TOLF_CA" -CRLfile "$TOLF_LOCK/new.pem" \
    -crl_check "$TOLF_CA" >/dev/null

crl_number() {
    TOLF_NUMBER="$(openssl crl -in "$1" -noout -crlnumber)"
    TOLF_HEX="${TOLF_NUMBER#crlNumber=0x}"
    test "$TOLF_HEX" != "$TOLF_NUMBER" || return 1
    case "$TOLF_HEX" in ''|*[!0-9a-fA-F]*) return 1 ;; esac
    test "${#TOLF_HEX}" -le 8 || return 1
    printf '%s\n' "$((0x$TOLF_HEX))"
}

TOLF_NEW_NUMBER="$(crl_number "$TOLF_LOCK/new.pem")"
if [ -f "$TOLF_CRL" ]; then
    TOLF_OLD_NUMBER="$(crl_number "$TOLF_CRL")"
    if [ "$TOLF_NEW_NUMBER" -lt "$TOLF_OLD_NUMBER" ]; then
        echo "ERROR: CRL rollback rejected" >&2
        exit 1
    fi
    if [ "$TOLF_NEW_NUMBER" -eq "$TOLF_OLD_NUMBER" ]; then
        if ! cmp -s "$TOLF_CRL" "$TOLF_LOCK/new.pem"; then
            echo "ERROR: conflicting CRL with the same number" >&2
            exit 1
        fi
        date +%s > "$TOLF_LAST_SYNC"
        exit 0
    fi
    cp -p "$TOLF_CRL" "$TOLF_LOCK/previous.pem"
fi

chmod 644 "$TOLF_LOCK/new.pem"
mv "$TOLF_LOCK/new.pem" "$TOLF_CRL"
if ! occtl -s "$TOLF_SOCKET" reload; then
    if [ -f "$TOLF_LOCK/previous.pem" ]; then
        mv "$TOLF_LOCK/previous.pem" "$TOLF_CRL"
    else
        rm -f "$TOLF_CRL"
    fi
    occtl -s "$TOLF_SOCKET" reload >/dev/null 2>&1 || true
    echo "ERROR: ocserv reload failed; previous CRL restored" >&2
    exit 1
fi
date +%s > "$TOLF_LAST_SYNC"
printf 'OK: signed CRL installed, number %s\n' "$TOLF_NEW_NUMBER"
