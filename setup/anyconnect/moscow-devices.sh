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
