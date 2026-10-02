#!/bin/sh
set -eu
TOLF_EXPECTED="${1:-}"
case "$TOLF_EXPECTED" in ''|*[!0-9a-f]*) echo 'Expected CA SHA256 argument' >&2; exit 2 ;; esac
test "${#TOLF_EXPECTED}" -eq 64
test "$(id -u)" -eq 0
TOLF_DIR=/etc/ocserv-moscow
TOLF_CONF="$TOLF_DIR/ocserv.conf"
TOLF_CRL="$TOLF_DIR/uk-client-ca.crl.pem"
TOLF_SOCKET=/var/run/occtl-moscow.socket
TOLF_SYNC=/usr/bin/tolf-oc-crl-sync
for TOLF_TOOL in openssl curl sha256sum occtl crontab cmp; do
    command -v "$TOLF_TOOL" >/dev/null
done
occtl -s "$TOLF_SOCKET" --json show users >/dev/null
TOLF_CURRENT="$(sed -n 's/^[[:space:]]*crl[[:space:]]*=[[:space:]]*//p' "$TOLF_CONF" | tr -d '"' | sed 's/[[:space:]]*$//')"
case "$TOLF_CURRENT" in ''|"$TOLF_CRL") ;; *) echo 'Existing CRL configuration needs integration' >&2; exit 1 ;; esac
TOLF_BACKUP="$(mktemp -d "$TOLF_DIR/crl-backup.XXXXXX")"
cp -p "$TOLF_CONF" "$TOLF_BACKUP/ocserv.conf"
mkdir -p /etc/crontabs
for TOLF_FILE in uk-client-ca.pem uk-client-ca.sha256 uk-client-ca.crl.pem; do
    if [ -f "$TOLF_DIR/$TOLF_FILE" ]; then cp -p "$TOLF_DIR/$TOLF_FILE" "$TOLF_BACKUP/$TOLF_FILE"; fi
done
if [ -f "$TOLF_SYNC" ]; then cp -p "$TOLF_SYNC" "$TOLF_BACKUP/sync.previous"; fi
if [ -f /etc/crontabs/root ]; then cp -p /etc/crontabs/root "$TOLF_BACKUP/cron.previous"; fi

curl -fsS --connect-timeout 10 --max-time 30 --max-filesize 65536 \
    https://api.tolf.is/oc/access/ca.pem -o "$TOLF_BACKUP/uk-ca.pem"
openssl x509 -in "$TOLF_BACKUP/uk-ca.pem" -outform DER -out "$TOLF_BACKUP/uk-ca.der"
test "$(sha256sum "$TOLF_BACKUP/uk-ca.der" | awk '{print $1}')" = "$TOLF_EXPECTED"
openssl verify -CAfile "$TOLF_DIR/tolf-client-ca.pem" "$TOLF_BACKUP/uk-ca.pem"
curl -fsS --connect-timeout 10 --max-time 30 --max-filesize 1048576 \
    https://api.tolf.is/oc/access/crl.pem -o "$TOLF_BACKUP/new-crl.pem"
openssl verify -CAfile "$TOLF_BACKUP/uk-ca.pem" \
    -CRLfile "$TOLF_BACKUP/new-crl.pem" -crl_check "$TOLF_BACKUP/uk-ca.pem"

cat > "$TOLF_BACKUP/sync.new" <<'TOLF_SYNC_SCRIPT'
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
TOLF_SYNC_SCRIPT
chmod 755 "$TOLF_BACKUP/sync.new"
sh -n "$TOLF_BACKUP/sync.new"

trap '
    TOLF_RC=$?
    if [ "$TOLF_RC" -ne 0 ]; then
        set +e
        cp -p "$TOLF_BACKUP/ocserv.conf" "$TOLF_CONF"
        for TOLF_FILE in uk-client-ca.pem uk-client-ca.sha256 uk-client-ca.crl.pem; do
            if [ -f "$TOLF_BACKUP/$TOLF_FILE" ]; then
                cp -p "$TOLF_BACKUP/$TOLF_FILE" "$TOLF_DIR/$TOLF_FILE"
            else rm -f "$TOLF_DIR/$TOLF_FILE"; fi
        done
        if [ -f "$TOLF_BACKUP/sync.previous" ]; then cp -p "$TOLF_BACKUP/sync.previous" "$TOLF_SYNC"; else rm -f "$TOLF_SYNC"; fi
        if [ -f "$TOLF_BACKUP/cron.previous" ]; then cp -p "$TOLF_BACKUP/cron.previous" /etc/crontabs/root; else rm -f /etc/crontabs/root; fi
        occtl -s "$TOLF_SOCKET" reload >/dev/null 2>&1
        /etc/init.d/cron restart >/dev/null 2>&1
        echo "ERROR: previous configuration restored. Backup: $TOLF_BACKUP" >&2
    fi
    exit "$TOLF_RC"
' EXIT

cp "$TOLF_BACKUP/uk-ca.pem" "$TOLF_DIR/uk-client-ca.pem"
printf '%s\n' "$TOLF_EXPECTED" > "$TOLF_DIR/uk-client-ca.sha256"
chmod 644 "$TOLF_DIR/uk-client-ca.pem" "$TOLF_DIR/uk-client-ca.sha256"
cp -p "$TOLF_BACKUP/sync.new" "$TOLF_SYNC"
# Initial sync validates the CRL number before replacing an existing list.
"$TOLF_SYNC"
if [ -z "$TOLF_CURRENT" ]; then
    test "$(grep -c '^[[:space:]]*ca-cert[[:space:]]*=' "$TOLF_CONF")" -eq 1
    cp -p "$TOLF_CONF" "$TOLF_BACKUP/config.new"
    awk -v crl="$TOLF_CRL" '{print} /^[[:space:]]*ca-cert[[:space:]]*=/ {print "crl = " crl}' \
        "$TOLF_CONF" > "$TOLF_BACKUP/config.new"
    mv "$TOLF_BACKUP/config.new" "$TOLF_CONF"
fi
occtl -s "$TOLF_SOCKET" reload
if [ -f /etc/crontabs/root ]; then
    sed '/# TOLF_OC_CRL_SYNC$/d' /etc/crontabs/root > "$TOLF_BACKUP/cron.new"
else : > "$TOLF_BACKUP/cron.new"; fi
printf '\n*/5 * * * * /usr/bin/tolf-oc-crl-sync >/dev/null 2>&1 || logger -t tolf-oc-crl "CRL synchronization failed" # TOLF_OC_CRL_SYNC\n' >> "$TOLF_BACKUP/cron.new"
chmod 600 "$TOLF_BACKUP/cron.new"
mv "$TOLF_BACKUP/cron.new" /etc/crontabs/root
/etc/init.d/cron enable
/etc/init.d/cron restart
"$TOLF_SYNC"
trap - EXIT
printf '\nOK: Moscow CRL enforcement configured.\nBackup: %s\n' "$TOLF_BACKUP"
openssl crl -in "$TOLF_CRL" -noout -issuer -lastupdate -nextupdate -crlnumber
grep '^[[:space:]]*crl[[:space:]]*=' "$TOLF_CONF"
crontab -l | sed -n '/TOLF_OC_CRL_SYNC/p'
occtl -s "$TOLF_SOCKET" --json show users
