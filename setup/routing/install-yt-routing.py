#!/usr/bin/env python3
"""Install the private YT routing mode on Riga and Moscow."""

import fcntl
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time


RIGA_CONF = Path("/etc/swanctl/conf.d/ikev2-riga-yt.conf")
RIGA_NFT = Path("/etc/nftables.conf")
RIGA_RULE = Path("/etc/systemd/system/tolf-yt-routing.service")
ROOT_HELPER = Path("/usr/local/sbin/tolf-provision-root")
SSH_HELPER = Path("/usr/local/sbin/tolf-provision-ssh")
LOCK = Path("/var/lock/tolf-yt-install.lock")
REMOTE = [
    "/usr/bin/ssh", "-T",
    "-i", "/root/.ssh/id_ed25519_ike_users_sync",
    "-o", "IdentitiesOnly=yes",
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=yes",
    "-o", "ConnectTimeout=10",
    "root@10.31.0.1", "sh -s",
]

CONNECTION = """connections {
    riga-yt {
        version = 2
        proposals = aes256-sha256-modp2048
        rekey_time = 0
        fragmentation = yes
        send_cert = always

        local {
            auth = pubkey
            certs = ikev2-riga.pem
            id = ikev2-riga.tolf.is
        }

        remote {
            auth = eap-mschapv2
            id = yt
            eap_id = %any
        }

        children {
            riga-yt {
                local_ts = 0.0.0.0/0
                esp_proposals = aes256-sha256
                rekey_time = 0
            }
        }

        pools = vpn-pool-riga-yt
    }
}

pools {
    vpn-pool-riga-yt {
        addrs = 10.18.0.0/24
        dns = 10.254.0.54
    }
}
"""

RULE_UNIT = """[Unit]
Description=TOLF YT source routing to Moscow
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=-/usr/sbin/ip -4 rule del priority 1023
ExecStart=/usr/sbin/ip -4 rule add priority 1023 from 10.18.0.0/24 table 102
ExecStop=-/usr/sbin/ip -4 rule del priority 1023

[Install]
WantedBy=multi-user.target
"""

REMOTE_SCRIPT = r'''#!/bin/sh
set -eu

POOL='10.18.0.0/24'
NFT='/etc/nftables.d/90-ru-split.nft'
BACKUP="/root/tolf-yt-moscow-backup-$(date +%Y%m%d-%H%M%S)-$$"

[ -f "$NFT" ] || { echo "Missing $NFT" >&2; exit 1; }
command -v uci >/dev/null
command -v nft >/dev/null
command -v fw4 >/dev/null
ip link show awgriga >/dev/null 2>&1
existing_rule="$(ip -4 rule show | grep '^10004:' || true)"
[ -z "$existing_rule" ] || echo "$existing_rule" | grep -q 'from 10.18.0.0/24 lookup 100' || {
    echo 'Moscow rule priority 10004 is already in use' >&2
    exit 1
}
HAD_RULE=0
HAD_ROUTE=0
HAD_ADDR=0
echo "$existing_rule" | grep -q 'from 10.18.0.0/24 lookup 100' && HAD_RULE=1 || true
ip -4 route show table main | grep -q '^10.18.0.0/24 dev awgriga' && HAD_ROUTE=1 || true
ip address show dev lo | grep -q '10.254.0.54/32' && HAD_ADDR=1 || true

mkdir -m 700 "$BACKUP"
cp -p /etc/config/network /etc/config/firewall /etc/config/dhcp "$NFT" "$BACKUP/"

restore() {
    cp -p "$BACKUP/network" /etc/config/network
    cp -p "$BACKUP/firewall" /etc/config/firewall
    cp -p "$BACKUP/dhcp" /etc/config/dhcp
    cp -p "$BACKUP/90-ru-split.nft" "$NFT"
    [ "$HAD_RULE" = 1 ] || ip -4 rule del priority 10004 2>/dev/null || true
    [ "$HAD_ROUTE" = 1 ] || ip -4 route del 10.18.0.0/24 dev awgriga 2>/dev/null || true
    [ "$HAD_ADDR" = 1 ] || ip address del 10.254.0.54/32 dev lo 2>/dev/null || true
    /etc/init.d/firewall reload >/dev/null 2>&1 || true
    /etc/init.d/dnsmasq restart >/dev/null 2>&1 || true
}
SUCCESS=0
trap 'if [ "$SUCCESS" != 1 ]; then restore; fi' EXIT HUP INT TERM

clone_uci() {
    package="$1" old="$2" new="$3" from="$4" to="$5"
    uci -q show "$package.$old" >/dev/null || {
        echo "Missing UCI section $package.$old" >&2
        exit 1
    }
    uci -q delete "$package.$new" || true
    uci show "$package.$old" |
        sed "s/^$package\\.$old/$package.$new/; s/$from/$to/g" |
        uci batch
}

clone_uci network riga_ikev2_sr riga_ikev2_yt '10\.16\.0\.0' '10.18.0.0'
clone_uci network riga_ikev2_sr_return riga_ikev2_yt_return '10\.16\.0\.0' '10.18.0.0'
uci set network.riga_ikev2_yt.priority='10004'

uci -q delete network.tolf_dns_yt || true
uci set network.tolf_dns_yt='interface'
uci set network.tolf_dns_yt.proto='static'
uci set network.tolf_dns_yt.device='lo'
uci set network.tolf_dns_yt.ipaddr='10.254.0.54'
uci set network.tolf_dns_yt.netmask='255.255.255.255'

clone_uci firewall riga_ikev2_sr_nat riga_ikev2_yt_nat '10\.16\.0\.0' '10.18.0.0'

uci -q delete dhcp.tolf_youtube || true
uci set dhcp.tolf_youtube='ipset'
uci add_list dhcp.tolf_youtube.name='yt_domains4'
for domain in \
    youtube.com youtu.be googlevideo.com ytimg.com \
    youtube-nocookie.com youtube.googleapis.com youtubei.googleapis.com \
    youtube-ui.l.google.com; do
    uci add_list dhcp.tolf_youtube.domain="$domain"
done

if ! grep -q '# TOLF YT routing v1' "$NFT"; then
    awk '
    /^chain ru_split_prerouting \{/ {
        if (split_seen++) exit 41
        print "set yt_domains4 {"
        print "    type ipv4_addr"
        print "    flags interval"
        print "}"
        print ""
        print
        print "    # TOLF YT routing v1"
        print "    ip saddr 10.18.0.0/24 ip daddr @ru4 meta mark set 0x100"
        print "    ip saddr 10.18.0.0/24 ip daddr @ru_domains4 meta mark set 0x100"
        print "    ip saddr 10.18.0.0/24 ip daddr @yt_domains4 meta mark set 0x100"
        next
    }
    /^chain policy_dns_redirect \{/ {
        if (dns_seen++) exit 42
        print
        print "    ip saddr 10.18.0.0/24 ip daddr != 10.254.0.54 udp dport 53 redirect to :53"
        print "    ip saddr 10.18.0.0/24 ip daddr != 10.254.0.54 tcp dport 53 redirect to :53"
        next
    }
    /^chain riga_ikev2_return_snat \{/ {
        if (snat_seen++) exit 43
        print
        print "    oifname \"gre4-riga_gre\" ip saddr 10.18.0.0/24 snat to 10.33.0.1"
        print "    oifname \"awgriga\" ip saddr 10.18.0.0/24 snat to 10.31.0.1"
        next
    }
    { print }
    END {
        if (split_seen != 1 || dns_seen != 1 || snat_seen != 1) exit 44
    }
    ' "$NFT" > /tmp/90-ru-split.yt.$$
    chmod "$(stat -c %a "$NFT")" /tmp/90-ru-split.yt.$$
    mv /tmp/90-ru-split.yt.$$ "$NFT"
fi

uci commit network
uci commit firewall
uci commit dhcp

fw4 check

ip -4 rule del priority 10004 2>/dev/null || true
ip -4 rule add priority 10004 from "$POOL" table 100
ip -4 route replace "$POOL" dev awgriga
ip address show dev lo | grep -q '10.254.0.54/32' || ip address add 10.254.0.54/32 dev lo

/etc/init.d/firewall reload
/etc/init.d/dnsmasq restart

ip -4 rule show | grep -q 'from 10.18.0.0/24 lookup 100'
ip -4 route show table main | grep -q '10.18.0.0/24 dev awgriga'
nft list set inet fw4 yt_domains4 >/dev/null
nft list chain inet fw4 ru_split_prerouting | grep -q '10.18.0.0/24.*yt_domains4'

SUCCESS=1
trap - EXIT HUP INT TERM
echo "Backup: $BACKUP"
echo 'Moscow YT routing: OK'
'''


def run(command, check=True, **kwargs):
    return subprocess.run(command, check=check, text=True, timeout=90, **kwargs)


def atomic(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def patch_once(source, old, new, description):
    if new in source:
        return source
    if source.count(old) != 1:
        raise RuntimeError(f"Unexpected {description}; nothing changed")
    return source.replace(old, new, 1)


def patch_riga_nft(source):
    source = patch_once(
        source,
        "10.17.0.0/24, 10.20.0.0/24",
        "10.17.0.0/24, 10.18.0.0/24, 10.20.0.0/24",
        "Riga NAT source list",
    )
    if "TOLF YT MSS v1" not in source:
        anchor = "table inet tolf_vpn_mss {"
        if source.count(anchor) != 1:
            raise RuntimeError("Unexpected Riga MSS table; nothing changed")
        block = """# TOLF YT MSS v1
table inet tolf_yt_mss {
    chain forward {
        type filter hook forward priority -139; policy accept;
        ip saddr 10.18.0.0/24 tcp flags & syn == syn tcp option maxseg size > 1200 counter tcp option maxseg size set 1200
        ip daddr 10.18.0.0/24 tcp flags & syn == syn tcp option maxseg size > 1200 counter tcp option maxseg size set 1200
    }
}

"""
        source = source.replace(anchor, block + anchor, 1)
    return source


def patch_helpers():
    root = ROOT_HELPER.read_text()
    root = patch_once(
        root,
        "riga:sr|riga:ru|moscow:",
        "riga:sr|riga:ru|riga:yt|moscow:",
        "provisioning Local ID allowlist",
    )
    ssh = SSH_HELPER.read_text()
    ssh = patch_once(
        ssh,
        "(sr|ru|lv|default)",
        "(sr|ru|lv|yt|default)",
        "SSH Local ID allowlist",
    )
    run(["/bin/bash", "-n"], input=root)
    run(["/bin/bash", "-n"], input=ssh)
    return root, ssh


def main():
    if os.geteuid() != 0 or socket.gethostname() != "EDISLV":
        raise SystemExit("Run as root on Riga EDISLV")
    if not RIGA_NFT.is_file() or not ROOT_HELPER.is_file() or not SSH_HELPER.is_file():
        raise SystemExit("Required Riga configuration is missing")
    rules = run(["/usr/sbin/ip", "-4", "rule", "show"], capture_output=True).stdout
    occupied = [line for line in rules.splitlines() if line.startswith("1023:")]
    if occupied and "from 10.18.0.0/24 lookup 102" not in occupied[0]:
        raise SystemExit("Riga rule priority 1023 is already in use")

    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        root, ssh = patch_helpers()
        nft = patch_riga_nft(RIGA_NFT.read_text())
        run(["/usr/sbin/nft", "-c", "-f", "/dev/stdin"], input=nft)

        probe = run(
            REMOTE,
            input="swanctl --list-conns --raw 2>/dev/null; ip link show awgriga 2>/dev/null\n",
            capture_output=True,
        )
        if "ikev2-eap-domain" not in probe.stdout or "awgriga" not in probe.stdout:
            raise RuntimeError("Unexpected Moscow provisioning endpoint")

        backup = Path("/root/tolf-yt-riga-backup-" + time.strftime("%Y%m%d-%H%M%S") + "-" + str(os.getpid()))
        backup.mkdir(mode=0o700)
        targets = {
            RIGA_CONF: CONNECTION,
            RIGA_NFT: nft,
            RIGA_RULE: RULE_UNIT,
            ROOT_HELPER: root,
            SSH_HELPER: ssh,
        }
        original = {}
        for path in targets:
            original[path] = path.read_bytes() if path.exists() else None
            if path.exists():
                shutil.copy2(path, backup / path.name)

        print("Riga backup:", backup, flush=True)
        try:
            for path, content in targets.items():
                mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
                atomic(path, content, mode)
            run(["/bin/systemctl", "daemon-reload"])
            run(["/bin/systemctl", "enable", "--now", "tolf-yt-routing.service"])
            run(["/usr/sbin/nft", "-f", str(RIGA_NFT)])
            run(["/usr/sbin/swanctl", "--load-conns"])
            run(["/usr/sbin/swanctl", "--load-pools"])
            checks = [
                (["/usr/sbin/ip", "-4", "rule", "show"], "from 10.18.0.0/24 lookup 102"),
                (["/usr/sbin/swanctl", "--list-conns", "--raw"], "riga-yt"),
                (["/usr/sbin/swanctl", "--list-pools", "--raw"], "vpn-pool-riga-yt"),
            ]
            for command, expected in checks:
                result = run(command, capture_output=True)
                if expected not in result.stdout:
                    raise RuntimeError("Riga validation failed: " + expected)

            remote = run(REMOTE, input=REMOTE_SCRIPT, capture_output=True)
            print(remote.stdout, end="")
        except Exception:
            if original.get(RIGA_RULE) is None:
                run(["/bin/systemctl", "disable", "--now", "tolf-yt-routing.service"], check=False)
            for path, content in original.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, content, path.stat().st_mode & 0o777 if path.exists() else 0o644)
            run(["/bin/systemctl", "daemon-reload"], check=False)
            if original.get(RIGA_RULE) is not None:
                run(["/bin/systemctl", "restart", "tolf-yt-routing.service"], check=False)
            run(["/usr/sbin/nft", "-f", str(RIGA_NFT)], check=False)
            run(["/usr/sbin/swanctl", "--load-conns"], check=False)
            run(["/usr/sbin/swanctl", "--load-pools"], check=False)
            raise

        print("OK: private YT routing mode installed.")
        print("Existing VPN credentials and sessions were not changed.")


if __name__ == "__main__":
    main()
