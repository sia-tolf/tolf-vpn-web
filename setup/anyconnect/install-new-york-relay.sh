#!/bin/ash
# Run on Moscow OpenWrt. Preparation is the default; activation is explicit.
set -eu
action="${1:---prepare}"
case "$action" in --prepare|--activate) ;; *) exit 2 ;; esac
ip -4 addr show dev br-lan | grep -F '92.243.66.204/' >/dev/null
command -v fw4 >/dev/null
backup=/root/tolf-backups/new-york-relay-20261024
mkdir -p "$backup"
chmod 700 "$backup"
test -f "$backup/firewall.before" || cp -p /etc/config/firewall "$backup/firewall.before"
candidate="$backup/uci.batch"
cat > "$candidate" <<'UCI'
set firewall.tolf_ny_relay_tcp=redirect
set firewall.tolf_ny_relay_tcp.name='TOLF New York relay TCP'
set firewall.tolf_ny_relay_tcp.src='lan'
set firewall.tolf_ny_relay_tcp.dest='lan'
set firewall.tolf_ny_relay_tcp.src_dip='92.243.66.204'
set firewall.tolf_ny_relay_tcp.src_dport='4443'
set firewall.tolf_ny_relay_tcp.dest_ip='162.252.174.201'
set firewall.tolf_ny_relay_tcp.dest_port='4443'
set firewall.tolf_ny_relay_tcp.proto='tcp'
set firewall.tolf_ny_relay_tcp.target='DNAT'
set firewall.tolf_ny_relay_tcp.reflection='0'
set firewall.tolf_ny_relay_tcp.family='ipv4'
set firewall.tolf_ny_relay_udp=redirect
set firewall.tolf_ny_relay_udp.name='TOLF New York relay DTLS'
set firewall.tolf_ny_relay_udp.src='lan'
set firewall.tolf_ny_relay_udp.dest='lan'
set firewall.tolf_ny_relay_udp.src_dip='92.243.66.204'
set firewall.tolf_ny_relay_udp.src_dport='443'
set firewall.tolf_ny_relay_udp.dest_ip='162.252.174.201'
set firewall.tolf_ny_relay_udp.dest_port='443'
set firewall.tolf_ny_relay_udp.proto='udp'
set firewall.tolf_ny_relay_udp.target='DNAT'
set firewall.tolf_ny_relay_udp.reflection='0'
set firewall.tolf_ny_relay_udp.family='ipv4'
set firewall.tolf_ny_relay_snat=nat
set firewall.tolf_ny_relay_snat.name='TOLF New York relay return path'
set firewall.tolf_ny_relay_snat.src='lan'
set firewall.tolf_ny_relay_snat.dest_ip='162.252.174.201'
set firewall.tolf_ny_relay_snat.dest_port='443 4443'
set firewall.tolf_ny_relay_snat.proto='tcp udp'
set firewall.tolf_ny_relay_snat.target='SNAT'
set firewall.tolf_ny_relay_snat.snat_ip='92.243.66.32'
set firewall.tolf_ny_relay_snat.family='ipv4'
UCI
chmod 600 "$candidate"
# Validate in a private UCI directory without changing live firewall configuration.
mkdir -p "$backup/candidate" "$backup/uci-state"
cp /etc/config/firewall "$backup/candidate/firewall"
uci -c "$backup/candidate" -t "$backup/uci-state" batch < "$candidate"
uci -c "$backup/candidate" -t "$backup/uci-state" commit firewall
echo "Prepared candidate: $backup/candidate/firewall"
if [ "$action" = --activate ]; then
    echo 'Activation requires the DNS, TLS and firewall review gates in docs/new-york-via-moscow.md.' >&2
    exit 3
fi
