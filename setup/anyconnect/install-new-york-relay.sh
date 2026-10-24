#!/bin/ash
# Dedicated Moscow ingress for New York; no changes to the shared fw4 table.
set -eu
action="${1:---prepare}"
case "$action" in --prepare|--activate) ;; *) exit 2 ;; esac
ip -4 addr show dev br-lan | grep -F '92.243.66.204/' >/dev/null
backup=/root/tolf-backups/new-york-relay-20261024
mkdir -p "$backup"
chmod 700 "$backup"
cat > "$backup/relay.nft.candidate" <<'NFT'
add table inet tolf_ny_relay
flush table inet tolf_ny_relay
table inet tolf_ny_relay {
 chain ingress {
  type nat hook prerouting priority -101; policy accept;
  iifname "br-lan" ip daddr 92.243.66.204 tcp dport { 80, 4443 } counter dnat ip to 162.252.174.201
  iifname "br-lan" ip daddr 92.243.66.204 udp dport 443 counter dnat ip to 162.252.174.201
 }
 chain return_path {
  type nat hook postrouting priority 99; policy accept;
  oifname "br-lan" ct original ip daddr 92.243.66.204 ip daddr 162.252.174.201 ct status dnat counter snat ip to 92.243.66.32
 }
}
NFT
nft -c -f "$backup/relay.nft.candidate"
[ "$action" = --activate ] || exit 0
test ! -f /etc/tolf-ny-relay.nft || cp -p /etc/tolf-ny-relay.nft "$backup/relay.nft.before"
cp "$backup/relay.nft.candidate" /etc/tolf-ny-relay.nft
chmod 600 /etc/tolf-ny-relay.nft
cat > /etc/init.d/tolf-ny-relay <<'INIT'
#!/bin/sh /etc/rc.common
START=96
STOP=10
start() {
 /usr/sbin/nft -c -f /etc/tolf-ny-relay.nft || return 1
 /usr/sbin/nft -f /etc/tolf-ny-relay.nft
}
reload() { start; }
stop() { /usr/sbin/nft delete table inet tolf_ny_relay 2>/dev/null || true; }
INIT
chmod 755 /etc/init.d/tolf-ny-relay
/etc/init.d/tolf-ny-relay start
/etc/init.d/tolf-ny-relay enable
