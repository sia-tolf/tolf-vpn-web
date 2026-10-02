#!/bin/sh
set -eu
test "$(id -u)" -eq 0
TOLF_DIR=/etc/ocserv-moscow
TOLF_CONF="$TOLF_DIR/ocserv.conf"
TOLF_SOCKET=/var/run/occtl-moscow.socket
for TOLF_TOOL in occtl nft openssl uci conntrack sha256sum; do command -v "$TOLF_TOOL" >/dev/null; done
test -s "$TOLF_DIR/uk-client-ca.crl.pem"
occtl -s "$TOLF_SOCKET" --json show users >/dev/null
for TOLF_OPTION in connect-script disconnect-script config-per-user; do
    TOLF_VALUE="$(sed -n "s/^[[:space:]]*$TOLF_OPTION[[:space:]]*=[[:space:]]*//p" "$TOLF_CONF" | tr -d '"' | sed 's/[[:space:]]*$//')"
    case "$TOLF_OPTION:$TOLF_VALUE" in
        connect-script:|disconnect-script:|config-per-user:|connect-script:/usr/bin/tolf-oc-device-hook|disconnect-script:/usr/bin/tolf-oc-device-hook|config-per-user:/etc/ocserv-moscow/config-per-user/) ;;
        *) echo "Existing $TOLF_OPTION needs integration" >&2; exit 1 ;;
    esac
done
test "$(grep -c '^[[:space:]]*ca-cert[[:space:]]*=' "$TOLF_CONF")" -eq 1
for TOLF_SET in ru4 ru_domains4 yt_domains4; do nft list set inet fw4 "$TOLF_SET" >/dev/null; done
TOLF_BACKUP="$(mktemp -d "$TOLF_DIR/devices-backup.XXXXXX")"
cp -p "$TOLF_CONF" "$TOLF_BACKUP/ocserv.conf"
cp -p /etc/config/firewall "$TOLF_BACKUP/firewall"
mkdir -p /usr/libexec "$TOLF_DIR/device-modes" "$TOLF_DIR/config-per-user" /var/run/tolf-oc-devices
chmod 700 "$TOLF_DIR/device-modes" /var/run/tolf-oc-devices
for TOLF_NAME in /usr/libexec/tolf-oc-devices /usr/bin/tolf-oc-device-hook /usr/bin/tolf-oc-devices-firewall /usr/bin/tolf-oc-remote /usr/bin/tolf-oc-mode; do
    if [ -f "$TOLF_NAME" ]; then cp -p "$TOLF_NAME" "$TOLF_BACKUP/${TOLF_NAME##*/}"; fi
done
cat > "$TOLF_BACKUP/devices.new" <<'TOLF_DEVICES_SCRIPT'
#!/bin/sh
# No certificates or account database here: public CNs, modes and live tunnel IPs.
set -eu
TOLF_DIR="${TOLF_OC_DIRECTORY:-/etc/ocserv-moscow}"
TOLF_RUN="${TOLF_OC_DEVICE_RUNTIME:-/var/run/tolf-oc-devices}"
TOLF_LOCK="${TOLF_OC_DEVICE_LOCK:-/tmp/tolf-oc-devices.lock}"
TOLF_SOCKET="${TOLF_OC_SOCKET:-/var/run/occtl-moscow.socket}"
TOLF_MODES="$TOLF_DIR/device-modes"

valid_cn() {
    case "$1" in tolf-oc-*) ;; *) return 1 ;; esac
    TOLF_HEX="${1#tolf-oc-}"
    case "$TOLF_HEX" in *[!0-9a-f]*) return 1 ;; esac
    [ "${#TOLF_HEX}" -eq 32 ]
}
valid_ip() {
    case "$1" in 10.21.0.*|10.22.0.*|10.23.0.*) ;; *) return 1 ;; esac
    TOLF_OCTET="${1##*.}"
    case "$TOLF_OCTET" in ''|*[!0-9]*|0*) return 1 ;; esac
    case "$1" in "10.21.0.$TOLF_OCTET"|"10.22.0.$TOLF_OCTET"|"10.23.0.$TOLF_OCTET") ;; *) return 1 ;; esac
    [ "$TOLF_OCTET" -ge 2 ] && [ "$TOLF_OCTET" -le 254 ]
}
valid_mode() { case "$1" in auto|ru|lv|yt) return 0 ;; *) return 1 ;; esac; }

acquire() {
    mkdir -p "$TOLF_RUN" "$TOLF_MODES" "$TOLF_DIR/config-per-user"
    chmod 700 "$TOLF_RUN" "$TOLF_MODES"
    TOLF_ATTEMPT=0
    until mkdir "$TOLF_LOCK" 2>/dev/null; do
        TOLF_ATTEMPT=$((TOLF_ATTEMPT + 1))
        [ "$TOLF_ATTEMPT" -le 10 ] || return 1
        sleep 1
    done
    chmod 700 "$TOLF_LOCK"
    trap 'rm -rf "$TOLF_LOCK"' EXIT
    trap 'exit 1' HUP INT TERM
}
release() { rm -rf "$TOLF_LOCK"; trap - EXIT HUP INT TERM; }

render() {
    if nft list chain inet fw4 tolf_oc_devices >/dev/null 2>&1; then
        echo 'delete chain inet fw4 tolf_oc_devices'
    fi
    for TOLF_MODE in auto ru lv yt deny; do
        if nft list set inet fw4 "tolf_oc_device_$TOLF_MODE" >/dev/null 2>&1; then
            printf 'delete set inet fw4 tolf_oc_device_%s\n' "$TOLF_MODE"
        fi
        printf 'add set inet fw4 tolf_oc_device_%s { type ipv4_addr; }\n' "$TOLF_MODE"
    done
    echo 'add chain inet fw4 tolf_oc_devices { type filter hook prerouting priority mangle + 5; policy accept; }'
    for TOLF_RECORD in "$TOLF_RUN"/tolf-oc-*; do
        [ -f "$TOLF_RECORD" ] || continue
        TOLF_BASENAME="${TOLF_RECORD##*/}"
        TOLF_CN="${TOLF_BASENAME%%.*}"
        valid_cn "$TOLF_CN" || return 1
        TOLF_IP="$(cat "$TOLF_RECORD")"
        valid_ip "$TOLF_IP" || return 1
        if [ -f "$TOLF_MODES/$TOLF_CN" ]; then
            TOLF_MODE="$(cat "$TOLF_MODES/$TOLF_CN")"
            valid_mode "$TOLF_MODE" || return 1
        else TOLF_MODE=deny; fi
        printf 'add element inet fw4 tolf_oc_device_%s { %s }\n' "$TOLF_MODE" "$TOLF_IP"
    done
    echo 'add rule inet fw4 tolf_oc_devices ip saddr @tolf_oc_device_deny counter drop'
    echo 'add rule inet fw4 tolf_oc_devices ip saddr @tolf_oc_device_ru meta mark set 0x100 counter'
    for TOLF_MODE in auto lv yt; do
        printf 'add rule inet fw4 tolf_oc_devices ip saddr @tolf_oc_device_%s meta mark set 0x200 counter\n' "$TOLF_MODE"
    done
    for TOLF_MODE in auto yt; do
        for TOLF_SET in ru4 ru_domains4; do
            printf 'add rule inet fw4 tolf_oc_devices ip saddr @tolf_oc_device_%s ip daddr @%s meta mark set 0x100 counter\n' "$TOLF_MODE" "$TOLF_SET"
        done
    done
    echo 'add rule inet fw4 tolf_oc_devices ip saddr @tolf_oc_device_yt ip daddr @yt_domains4 meta mark set 0x100 counter'
}
apply_rules() {
    render > "$TOLF_LOCK/rules.nft" || return 1
    nft -c -f "$TOLF_LOCK/rules.nft" || return 1
    nft -f "$TOLF_LOCK/rules.nft"
}
clear_connections() {
    if command -v conntrack >/dev/null 2>&1; then
        for TOLF_RECORD in "$TOLF_RUN/$1".*; do
            [ -f "$TOLF_RECORD" ] || continue
            TOLF_IP="$(cat "$TOLF_RECORD")"
            valid_ip "$TOLF_IP" || return 1
            conntrack -D -f ipv4 -s "$TOLF_IP" >/dev/null 2>&1 || true
        done
    fi
}

case "${1:-}" in
    hook)
        TOLF_USER="${USERNAME:-}"
        case "$TOLF_USER" in tolf-oc-*) valid_cn "$TOLF_USER" || exit 1 ;; *) TOLF_USER=legacy ;; esac
        TOLF_ID="${ID:-}"
        case "$TOLF_ID" in ''|*[!0-9]*) exit 1 ;; esac
        [ "${#TOLF_ID}" -le 20 ]
        TOLF_IP="${IP_REMOTE:-}"
        valid_ip "$TOLF_IP"
        acquire
        case "${REASON:-}" in
            connect)
                # Remove stale leases before an IP is reused, including by the pilot.
                for TOLF_RECORD in "$TOLF_RUN"/tolf-oc-* "$TOLF_RUN"/legacy.*; do
                    [ -f "$TOLF_RECORD" ] || continue
                    if [ "$(cat "$TOLF_RECORD")" = "$TOLF_IP" ]; then rm -f "$TOLF_RECORD"; fi
                done
                if [ "$TOLF_USER" != legacy ]; then
                    [ -f "$TOLF_MODES/$TOLF_USER" ] || exit 1
                    valid_mode "$(cat "$TOLF_MODES/$TOLF_USER")"
                    printf '%s\n' "$TOLF_IP" > "$TOLF_RUN/$TOLF_USER.$TOLF_ID"
                else
                    printf '%s\n' "$TOLF_IP" > "$TOLF_RUN/legacy.$TOLF_ID"
                fi
                if ! apply_rules; then
                    rm -f "$TOLF_RUN/$TOLF_USER.$TOLF_ID"
                    exit 1
                fi
                ;;
            disconnect)
                TOLF_RECORD="$TOLF_RUN/$TOLF_USER.$TOLF_ID"
                if [ -f "$TOLF_RECORD" ] && [ "$(cat "$TOLF_RECORD")" = "$TOLF_IP" ]; then rm -f "$TOLF_RECORD"; fi
                apply_rules
                ;;
            *) exit 1 ;;
        esac
        ;;
    set)
        [ "$#" -eq 3 ]; valid_cn "$2"; valid_mode "$3"
        TOLF_USER="$2"; TOLF_NEW_MODE="$3"
        acquire
        TOLF_OLD_MODE=""
        if [ -f "$TOLF_MODES/$TOLF_USER" ]; then TOLF_OLD_MODE="$(cat "$TOLF_MODES/$TOLF_USER")"; valid_mode "$TOLF_OLD_MODE"; fi
        printf '%s\n' "$TOLF_NEW_MODE" > "$TOLF_LOCK/mode.new"
        chmod 600 "$TOLF_LOCK/mode.new"
        mv "$TOLF_LOCK/mode.new" "$TOLF_MODES/$TOLF_USER"
        if ! apply_rules; then
            if [ -n "$TOLF_OLD_MODE" ]; then printf '%s\n' "$TOLF_OLD_MODE" > "$TOLF_MODES/$TOLF_USER"; else rm -f "$TOLF_MODES/$TOLF_USER"; fi
            exit 1
        fi
        printf 'max-same-clients = 1\n' > "$TOLF_DIR/config-per-user/$TOLF_USER"
        if [ "$TOLF_OLD_MODE" != "$TOLF_NEW_MODE" ]; then clear_connections "$TOLF_USER"; fi
        printf '{"status":"ok","username":"%s","mode":"%s"}\n' "$TOLF_USER" "$TOLF_NEW_MODE"
        ;;
    remove)
        [ "$#" -eq 2 ]; valid_cn "$2"; TOLF_USER="$2"
        acquire
        rm -f "$TOLF_MODES/$TOLF_USER" "$TOLF_DIR/config-per-user/$TOLF_USER"
        # Live leases become denied before releasing the lock and disconnecting.
        apply_rules
        clear_connections "$TOLF_USER"
        release
        occtl -s "$TOLF_SOCKET" disconnect user "$TOLF_USER" >/dev/null 2>&1 || true
        occtl -s "$TOLF_SOCKET" --json show users >/dev/null
        if occtl -s "$TOLF_SOCKET" --json show user "$TOLF_USER" >/dev/null 2>&1; then
            echo '{"status":"error","error":"device_still_connected"}'; exit 1
        else TOLF_RC=$?; [ "$TOLF_RC" -eq 2 ] || exit 1; fi
        printf '{"status":"ok","username":"%s","removed":true}\n' "$TOLF_USER"
        ;;
    session)
        [ "$#" -eq 2 ]; valid_cn "$2"; TOLF_USER="$2"
        occtl -s "$TOLF_SOCKET" --json show users >/dev/null
        if occtl -s "$TOLF_SOCKET" --json show user "$TOLF_USER" >/dev/null 2>&1; then TOLF_CONNECTED=true
        else TOLF_RC=$?; [ "$TOLF_RC" -eq 2 ] || exit 1; TOLF_CONNECTED=false; fi
        printf '{"status":"ok","username":"%s","connected":%s}\n' "$TOLF_USER" "$TOLF_CONNECTED"
        ;;
    apply)
        [ "$#" -eq 1 ]; acquire; apply_rules
        ;;
    pilot-clear)
        [ "$#" -eq 1 ]; acquire
        for TOLF_RECORD in "$TOLF_RUN"/legacy.*; do
            [ -f "$TOLF_RECORD" ] || continue
            TOLF_IP="$(cat "$TOLF_RECORD")"; valid_ip "$TOLF_IP"
            case "$TOLF_IP" in 10.21.0.*) conntrack -D -f ipv4 -s "$TOLF_IP" >/dev/null 2>&1 || true ;; esac
        done
        ;;
    health)
        [ "$#" -eq 1 ]
        TOLF_CA="$TOLF_DIR/uk-client-ca.pem"
        TOLF_EXPECTED="$(cat "$TOLF_DIR/uk-client-ca.sha256")"
        [ "${#TOLF_EXPECTED}" -eq 64 ]; case "$TOLF_EXPECTED" in *[!0-9a-f]*) exit 1 ;; esac
        TOLF_ACTUAL="$(openssl x509 -in "$TOLF_CA" -noout -fingerprint -sha256 | sed 's/.*=//' | tr -d ':' | tr 'A-F' 'a-f')"
        [ "$TOLF_ACTUAL" = "$TOLF_EXPECTED" ]
        grep -Fx 'connect-script = /usr/bin/tolf-oc-device-hook' "$TOLF_DIR/ocserv.conf" >/dev/null
        grep -Fx 'disconnect-script = /usr/bin/tolf-oc-device-hook' "$TOLF_DIR/ocserv.conf" >/dev/null
        grep -Fx "config-per-user = $TOLF_DIR/config-per-user/" "$TOLF_DIR/ocserv.conf" >/dev/null
        openssl verify -CAfile "$TOLF_CA" -CRLfile "$TOLF_DIR/uk-client-ca.crl.pem" -crl_check "$TOLF_CA" >/dev/null
        occtl -s "$TOLF_SOCKET" --json show users >/dev/null
        nft list chain inet fw4 tolf_oc_devices >/dev/null
        printf '{"status":"ok","version":1,"caSha256":"%s","deviceRouting":true,"issuance":false}\n' "$TOLF_EXPECTED"
        ;;
    *) echo 'Unsupported device operation' >&2; exit 2 ;;
esac
TOLF_DEVICES_SCRIPT
cat > "$TOLF_BACKUP/remote.new" <<'TOLF_REMOTE_SCRIPT'
#!/bin/sh
set -eu
# The original pilot commands remain supported. No eval, shell or arbitrary argv.
case "${SSH_ORIGINAL_COMMAND:-}" in
    'tolf-oc-node-health') exec /usr/libexec/tolf-oc-devices health ;;
    'tolf-oc-crl-sync') /usr/bin/tolf-oc-crl-sync >/dev/null; exec /usr/libexec/tolf-oc-devices health ;;
    'tolf-oc-session pilot-tolf')
        occtl -s /var/run/occtl-moscow.socket --json show users >/dev/null
        if occtl -s /var/run/occtl-moscow.socket --json show user pilot-tolf >/dev/null 2>&1; then TOLF_CONNECTED=true
        else TOLF_RC=$?; [ "$TOLF_RC" -eq 2 ] || exit 1; TOLF_CONNECTED=false; fi
        printf '{"status":"ok","username":"pilot-tolf","connected":%s}\n' "$TOLF_CONNECTED"
        exit 0 ;;
    'tolf-oc-mode auto') TOLF_MODE=auto ;;
    'tolf-oc-mode ru') TOLF_MODE=ru ;;
    'tolf-oc-mode lv') TOLF_MODE=lv ;;
    'tolf-oc-mode yt') TOLF_MODE=yt ;;
    *)
        case "${SSH_ORIGINAL_COMMAND:-}" in
            *[!a-z0-9\ -]*) echo '{"status":"error","error":"command_not_allowed"}'; exit 1 ;;
        esac
        set -f
        IFS=' '
        set -- ${SSH_ORIGINAL_COMMAND:-}
        case "${1:-}" in
            tolf-oc-device)
                [ "$#" -eq 3 ]; exec /usr/libexec/tolf-oc-devices set "$2" "$3" ;;
            tolf-oc-device-remove)
                [ "$#" -eq 2 ]; exec /usr/libexec/tolf-oc-devices remove "$2" ;;
            tolf-oc-session)
                [ "$#" -eq 2 ]; exec /usr/libexec/tolf-oc-devices session "$2" ;;
            *) echo '{"status":"error","error":"command_not_allowed"}'; exit 1 ;;
        esac ;;
esac
/usr/bin/tolf-oc-mode "$TOLF_MODE" >/dev/null
printf '{"status":"ok","mode":"%s"}\n' "$TOLF_MODE"
TOLF_REMOTE_SCRIPT
sh -n "$TOLF_BACKUP/devices.new"
sh -n "$TOLF_BACKUP/remote.new"
trap '
    TOLF_RC=$?
    if [ "$TOLF_RC" -ne 0 ]; then
        set +e
        cp -p "$TOLF_BACKUP/ocserv.conf" "$TOLF_CONF"
        cp -p "$TOLF_BACKUP/firewall" /etc/config/firewall
        for TOLF_NAME in /usr/libexec/tolf-oc-devices /usr/bin/tolf-oc-device-hook /usr/bin/tolf-oc-devices-firewall /usr/bin/tolf-oc-remote /usr/bin/tolf-oc-mode; do
            if [ -f "$TOLF_BACKUP/${TOLF_NAME##*/}" ]; then cp -p "$TOLF_BACKUP/${TOLF_NAME##*/}" "$TOLF_NAME"; else rm -f "$TOLF_NAME"; fi
        done
        /etc/init.d/firewall reload >/dev/null 2>&1
        occtl -s "$TOLF_SOCKET" reload >/dev/null 2>&1
        echo "ERROR: previous configuration restored. Backup: $TOLF_BACKUP" >&2
    fi
    exit "$TOLF_RC"
' EXIT
cp "$TOLF_BACKUP/devices.new" /usr/libexec/tolf-oc-devices
cp "$TOLF_BACKUP/remote.new" /usr/bin/tolf-oc-remote
printf '#!/bin/sh\nexec /usr/libexec/tolf-oc-devices hook\n' > /usr/bin/tolf-oc-device-hook
printf '#!/bin/sh\nexec /usr/libexec/tolf-oc-devices apply\n' > /usr/bin/tolf-oc-devices-firewall
chmod 755 /usr/libexec/tolf-oc-devices /usr/bin/tolf-oc-remote /usr/bin/tolf-oc-device-hook /usr/bin/tolf-oc-devices-firewall
grep -E 'conntrack -D -f ipv4 -s 10\.21\.0\.0/24|tolf-oc-devices pilot-clear' /usr/bin/tolf-oc-mode >/dev/null
cp -p /usr/bin/tolf-oc-mode "$TOLF_BACKUP/mode.new"
sed 's|conntrack -D -f ipv4 -s 10\.21\.0\.0/24|/usr/libexec/tolf-oc-devices pilot-clear|' \
    /usr/bin/tolf-oc-mode > "$TOLF_BACKUP/mode.new"
sh -n "$TOLF_BACKUP/mode.new"
mv "$TOLF_BACKUP/mode.new" /usr/bin/tolf-oc-mode
cp -p "$TOLF_CONF" "$TOLF_BACKUP/config.new"
awk '
    /^[[:space:]]*(connect-script|disconnect-script|config-per-user)[[:space:]]*=/ {next}
    {print}
    /^[[:space:]]*ca-cert[[:space:]]*=/ {
        print "config-per-user = /etc/ocserv-moscow/config-per-user/"
        print "connect-script = /usr/bin/tolf-oc-device-hook"
        print "disconnect-script = /usr/bin/tolf-oc-device-hook"
    }
' "$TOLF_CONF" > "$TOLF_BACKUP/config.new"
/usr/sbin/ocserv -t -c "$TOLF_BACKUP/config.new"
mv "$TOLF_BACKUP/config.new" "$TOLF_CONF"
uci set firewall.tolf_oc_devices='include'
uci set firewall.tolf_oc_devices.type='script'
uci set firewall.tolf_oc_devices.path='/usr/bin/tolf-oc-devices-firewall'
uci set firewall.tolf_oc_devices.fw4_compatible='1'
uci commit firewall
/etc/init.d/firewall reload
/usr/libexec/tolf-oc-devices apply
occtl -s "$TOLF_SOCKET" reload
SSH_ORIGINAL_COMMAND=tolf-oc-node-health /usr/bin/tolf-oc-remote
trap - EXIT
printf '\nOK: Moscow personal device control installed.\nBackup: %s\n' "$TOLF_BACKUP"
echo 'Personal certificate issuance remains disabled on UK.'
nft list chain inet fw4 tolf_oc_devices
