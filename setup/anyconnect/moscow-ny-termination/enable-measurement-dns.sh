#!/bin/sh
# Permit only this published private measurement hostname through dnsmasq's
# rebinding protection; do not disable protection globally.
set -eu
backup=/root/tolf-backups/ny-termination-20261024/dhcp.before-speedtest-dns
test -f "$backup" || cp -p /etc/config/dhcp "$backup"
uci -q del_list dhcp.@dnsmasq[0].rebind_domain=speedtest-us.vpn.tolf.is || true
uci add_list dhcp.@dnsmasq[0].rebind_domain=speedtest-us.vpn.tolf.is
uci commit dhcp
/etc/init.d/dnsmasq restart
