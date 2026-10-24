#!/bin/sh
# Dedicated measurement address, outside ocserv client pools.
set -eu
backup=/root/tolf-backups/ny-termination-20261024/dhcp.before-stable-moscow-measurement
test -f "$backup" || cp -p /etc/config/dhcp "$backup"
cat > /etc/init.d/tolf-moscow-measurement-address <<'EOF'
#!/bin/sh /etc/rc.common
START=50
STOP=10
start() {
 ip -4 address show dev lo | grep -q 'inet 10.250.82.1/32' || ip address add 10.250.82.1/32 dev lo
}
stop() {
 ip address del 10.250.82.1/32 dev lo 2>/dev/null || true
}
EOF
chmod 755 /etc/init.d/tolf-moscow-measurement-address
/etc/init.d/tolf-moscow-measurement-address enable
/etc/init.d/tolf-moscow-measurement-address start
uci set dhcp.tolf_moscow_measurement=domain
uci set dhcp.tolf_moscow_measurement.name=speedtest.vpn.tolf.is
uci set dhcp.tolf_moscow_measurement.ip=10.250.82.1
uci commit dhcp
/etc/init.d/dnsmasq restart
