#!/usr/bin/env python3
"""Install the reviewed Riga VPN-only measurement listener. No VPN restart."""
import argparse, hashlib, json, subprocess
from pathlib import Path

EXPECTED_BACKEND = "baf5095832b6009d51e64579b153d3ba4f43603b18c353bc7d665dc12bb5dacb"
UNIT_NAME = "tolf-vpn-measurement.service"
FILES = {
 "/etc/tolf-vpn-measurement.toml": (0o644, '''bind_address = "10.250.80.1"
listen_port = 8444
proxyprotocol_port = 0
assets_path = ""
database_type = "none"
redact_ip_addresses = true
enable_tls = true
enable_http2 = false
tls_cert_file = "/run/credentials/tolf-vpn-measurement.service/tls-chain"
tls_key_file = "/run/credentials/tolf-vpn-measurement.service/tls-key"
'''),
 "/etc/systemd/system/tolf-vpn-measurement.service": (0o644, '''[Unit]
Description=TOLF VPN-only connection measurement
After=network-online.target
Wants=network-online.target

[Service]
DynamicUser=yes
ExecStart=/usr/local/bin/speedtest-backend -c /etc/tolf-vpn-measurement.toml
LoadCredential=tls-chain:/etc/letsencrypt/live/tolf-vpn-wildcard/fullchain.pem
LoadCredential=tls-key:/etc/letsencrypt/live/tolf-vpn-wildcard/privkey.pem
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
MemoryMax=512M
TasksMax=256
LimitNOFILE=8192

[Install]
WantedBy=multi-user.target
'''),
 "/etc/letsencrypt/renewal-hooks/deploy/80-tolf-vpn-measurement": (0o755, '''#!/bin/sh
if [ "$RENEWED_LINEAGE" = "/etc/letsencrypt/live/tolf-vpn-wildcard" ]; then
    systemctl try-restart tolf-vpn-measurement.service
fi
''')
}

def run(args):
 return subprocess.run(args, capture_output=True, text=True, check=True, timeout=15).stdout

def validate():
 binary=Path("/usr/local/bin/speedtest-backend")
 assert hashlib.sha256(binary.read_bytes()).hexdigest()==EXPECTED_BACKEND, "Backend differs from reviewed build"
 addresses=json.loads(run(["ip","-j","-4","addr","show","dev","lo"]))
 assert any(a.get("local")=="10.250.80.1" for link in addresses for a in link.get("addr_info",[])), "Existing Riga loopback address is absent"
 for name in ["fullchain.pem","privkey.pem"]:
  assert (Path("/etc/letsencrypt/live/tolf-vpn-wildcard")/name).exists()
 for filename,(_,text) in FILES.items():
  path=Path(filename)
  assert not path.exists() or path.read_text()==text, "Unmanaged file collision: "+filename

def apply():
 validate()
 created=[]
 try:
  for filename,(mode,text) in FILES.items():
   path=Path(filename)
   if not path.exists():
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text);path.chmod(mode);created.append(path)
  run(["systemctl","daemon-reload"])
  run(["systemctl","enable","--now",UNIT_NAME])
  run(["systemctl","is-active",UNIT_NAME])
 except BaseException:
  run(["systemctl","disable","--now",UNIT_NAME])
  for path in reversed(created):path.unlink(missing_ok=True)
  run(["systemctl","daemon-reload"])
  raise
 return {"status":"active","address":"10.250.80.1:8444","vpn_restarted":False}

def rollback():
 for filename,(_,text) in FILES.items():
  path=Path(filename)
  assert not path.exists() or path.read_text()==text, "Refusing to remove an unmanaged file"
 run(["systemctl","disable","--now",UNIT_NAME])
 for filename in FILES:Path(filename).unlink(missing_ok=True)
 run(["systemctl","daemon-reload"])
 return {"status":"removed","vpn_restarted":False}

if __name__=="__main__":
 parser=argparse.ArgumentParser()
 group=parser.add_mutually_exclusive_group()
 group.add_argument("--apply",action="store_true")
 group.add_argument("--rollback",action="store_true")
 args=parser.parse_args()
 if args.apply:result=apply()
 elif args.rollback:result=rollback()
 else:
  validate()
  result={"status":"checks_passed_no_changes","files":list(FILES),"address":"10.250.80.1:8444"}
 print(json.dumps(result))
