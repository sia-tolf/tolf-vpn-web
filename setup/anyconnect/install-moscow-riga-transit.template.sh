#!/bin/sh
set -eu

ip -4 addr show dev br-lan | grep -q 'inet 92\.243\.66\.32/24 ' || {
    echo 'ERROR: run this installer only on the Moscow OpenWrt node.' >&2
    exit 1
}
test -f /etc/ocserv-moscow/ocserv.conf
ip link show dev gre4-riga_gre >/dev/null
[ -z "$(uci changes firewall)" ] || {
    echo 'ERROR: commit or revert existing firewall changes before this installer.' >&2
    exit 1
}

HELPER=/usr/bin/tolf-oc-riga-transit
BACKUP="$(mktemp -d /etc/ocserv-moscow/riga-transit-backup.XXXXXX)"
cp -p /etc/config/firewall "$BACKUP/firewall"
if [ -e "$HELPER" ]; then
    test ! -L "$HELPER"
    cp -p "$HELPER" "$BACKUP/helper"
fi
CURRENT="$(ip -4 rule show | awk '$1 == "8983:" { print }')"
EXISTING="$(uci -q get firewall.tolf_oc_riga_transit.path || true)"
if [ -n "$EXISTING" ] && [ "$EXISTING" != "$HELPER" ]; then
    echo 'ERROR: existing transit include needs integration.' >&2
    exit 1
fi

trap '
    RC=$?
    if [ "$RC" -ne 0 ]; then
        set +e
        uci revert firewall
        cp -p "$BACKUP/firewall" /etc/config/firewall
        if [ -f "$BACKUP/helper" ]; then
            cp -p "$BACKUP/helper" "$HELPER"
        else
            rm -f "$HELPER"
        fi
        if [ -z "$CURRENT" ]; then ip -4 rule del priority 8983; fi
        /etc/init.d/firewall reload
        echo "ERROR: original configuration restored. Backup: $BACKUP" >&2
    fi
    exit "$RC"
' EXIT

cat > "$BACKUP/helper.new" <<'TOLF_TRANSIT_SCRIPT'
# BUILD_TRANSIT_SCRIPT
TOLF_TRANSIT_SCRIPT
chmod 755 "$BACKUP/helper.new"
sh "$BACKUP/helper.new"
cp -p "$BACKUP/helper.new" "$HELPER"

uci set firewall.tolf_oc_riga_transit='include'
uci set firewall.tolf_oc_riga_transit.type='script'
uci set firewall.tolf_oc_riga_transit.path="$HELPER"
uci set firewall.tolf_oc_riga_transit.fw4_compatible='1'
uci -q delete firewall.tolf_oc_riga_transit.reload || true
uci commit firewall
/etc/init.d/firewall reload

ROUTE="$(ip -4 route get 1.1.1.1 from 10.19.0.42 iif gre4-riga_gre mark 0x200)"
printf '%s\n' "$ROUTE" | grep -q 'via 92\.243\.66\.1 dev br-lan' || {
    echo 'ERROR: Riga transit still does not use Moscow egress.' >&2
    exit 1
}
printf '%s\n' "$ROUTE"
ip -4 rule show | awk '$1 == "8983:" { print }'
echo "OK: Riga-selected transit uses Moscow egress. Backup: $BACKUP"
trap - EXIT
