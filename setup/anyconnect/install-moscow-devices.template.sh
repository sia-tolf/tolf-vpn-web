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
# BUILD_DEVICES_SCRIPT
TOLF_DEVICES_SCRIPT
cat > "$TOLF_BACKUP/remote.new" <<'TOLF_REMOTE_SCRIPT'
# BUILD_REMOTE_SCRIPT
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
