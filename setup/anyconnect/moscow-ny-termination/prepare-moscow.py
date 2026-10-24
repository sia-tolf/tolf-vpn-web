#!/usr/bin/env python3
import subprocess,json,base64
from pathlib import Path
BASE=Path(__file__).resolve().parent
SSH=['ssh','-T','-i','/opt/tolf-mcp/moscow_ed25519','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/opt/tolf-api/.ssh/known_hosts','root@92.243.66.204']
def remote(script):
 r=subprocess.run(SSH+['python3','-'],input=script,text=True,capture_output=True,timeout=40)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
files=['/usr/libexec/tolf-oc-devices','/usr/libexec/tolf-oc-external-exit','/usr/libexec/tolf-oc-nft-accounting','/usr/libexec/tolf-oc-traffic-collector','/usr/libexec/tolf-oc-traffic-recovery','/etc/ocserv-moscow/ocserv.conf']
data=json.loads(remote("import json\nfrom pathlib import Path\nprint(json.dumps({p:((Path('/root/tolf-backups/ny-termination-20261024')/p.lstrip('/')).read_text() if (Path('/root/tolf-backups/ny-termination-20261024')/p.lstrip('/')).exists() else Path(p).read_text()) for p in "+repr(files)+"}))"))
out={}
def change(path,a,b):
 s=out.get(path,data[path]);assert a in s,(path,a);out[path]=s.replace(a,b)
path=files[0]
change(path,'10.21.0.*|10.22.0.*|10.23.0.*','10.21.0.*|10.22.0.*|10.23.0.*|10.24.0.*')
change(path,'"10.23.0.$TOLF_OCTET")','"10.23.0.$TOLF_OCTET"|"10.24.0.$TOLF_OCTET")')
change(path,'occtl -s "$TOLF_SOCKET" disconnect user "$TOLF_USER" >/dev/null 2>&1 || true','''occtl -s "$TOLF_SOCKET" disconnect user "$TOLF_USER" >/dev/null 2>&1 || true
        if [ -S /var/run/occtl-ny-moscow.socket ]; then occtl -s /var/run/occtl-ny-moscow.socket disconnect user "$TOLF_USER" >/dev/null 2>&1 || true; fi''')
old='''        occtl -s "$TOLF_SOCKET" --json show users >/dev/null
        if occtl -s "$TOLF_SOCKET" --json show user "$TOLF_USER" >/dev/null 2>&1; then'''
new='''        TOLF_ONLINE="$(/usr/libexec/tolf-oc-users "$TOLF_USER")"
        if [ "$TOLF_ONLINE" = true ]; then'''
change(path,old,new)
change(path,'else TOLF_RC=$?; [ "$TOLF_RC" -eq 2 ] || exit 1; TOLF_CONNECTED=false; fi','else TOLF_CONNECTED=false; fi')
change(path,'else TOLF_RC=$?; [ "$TOLF_RC" -eq 2 ] || exit 1; fi','else :; fi')
path=files[1]
change(path,"choice=registry.get(cn,'riga')","choice='all_us' if f.read_text().strip().startswith('10.24.0.') else registry.get(cn,'riga')")
change(path,"'10.23.0.0/24']","'10.23.0.0/24','10.24.0.0/24']")
path=files[2]
change(path,'(21|22|23)','(21|22|23|24)')
for path in files[3:5]:
 old='["occtl", "-s", SOCKET, "--json", "show", "users"]' if path==files[3] else '["occtl","-s",SOCKET,"--json","show","users"]'
 change(path,old,'["/usr/libexec/tolf-oc-users"]')
out['/usr/libexec/tolf-oc-users']=r"""#!/usr/bin/python3
import json,subprocess,sys,re
from pathlib import Path
users=[]
for socket,entry in [('/var/run/occtl-moscow.socket','moscow'),('/var/run/occtl-ny-moscow.socket','us')]:
 if entry=='us' and not Path(socket).exists():continue
 p=subprocess.run(['occtl','-s',socket,'--json','show','users'],capture_output=True,text=True,timeout=15,check=True)
 rows=json.loads(p.stdout)
 if not isinstance(rows,list):raise ValueError('Invalid session inventory')
 for row in rows:row['TolfEntry']=entry
 users.extend(rows)
if len(sys.argv)==2:
 cn=sys.argv[1]
 if not re.fullmatch(r'tolf-oc-[0-9a-f]{32}',cn):raise ValueError('Invalid identity')
 print('true' if any(u.get('Username')==cn for u in users) else 'false')
elif len(sys.argv)==1:print(json.dumps(users))
else:raise ValueError('Invalid arguments')
"""
conf=data[files[5]]
replacements={
'listen-host = 92.243.66.32':'listen-host = 92.243.66.204',
'server-cert = /etc/acme/oc.tolf.is_ecc/fullchain.cer':'server-cert = /etc/ocserv-ny-moscow/fullchain.pem',
'server-key = /etc/acme/oc.tolf.is_ecc/oc.tolf.is.key':'server-key = /etc/ocserv-ny-moscow/privkey.pem',
'device = vpns-mow':'device = vpns-mowN',
'ipv4-network = 10.21.0.0':'ipv4-network = 10.24.0.0',
'/var/run/occtl-moscow.socket':'/var/run/occtl-ny-moscow.socket',
'/var/run/ocserv-moscow-socket':'/var/run/ocserv-ny-moscow-socket',
'/var/run/ocserv-moscow.pid':'/var/run/ocserv-ny-moscow.pid'}
for a,b in replacements.items():assert a in conf,a;conf=conf.replace(a,b)
conf='\n'.join(l for l in conf.splitlines() if not l.startswith(('config-per-group =','select-group =','default-select-group =')))+'\n'
conf+='route = default\nno-route = 92.243.66.204/32\nmtu = 1380\n'
out['/etc/ocserv-ny-moscow/ocserv.conf']=conf
out['/etc/init.d/ocserv-ny-moscow']="""#!/bin/sh /etc/rc.common
START=97
STOP=8
USE_PROCD=1
start_service() {
 /usr/libexec/tolf-oc-devices apply || return 1
 procd_open_instance
 procd_set_param command /usr/sbin/ocserv -d 4 -s -f -c /etc/ocserv-ny-moscow/ocserv.conf
 procd_set_param respawn
 procd_set_param stdout 1
 procd_set_param stderr 1
 procd_close_instance
}
"""
relay=remote("from pathlib import Path\nprint(Path('/etc/tolf-ny-relay.nft').read_text(),end='')")
out['/etc/tolf-ny-relay.nft']='\n'.join(l for l in relay.splitlines() if 'udp dport' not in l).replace('tcp dport { 80, 4443 }','tcp dport 80')
assert '4443' not in out['/etc/tolf-ny-relay.nft'],out['/etc/tolf-ny-relay.nft']
payload=base64.b64encode(json.dumps(out).encode()).decode()
apply="""import json,base64,shutil,subprocess
from pathlib import Path
files=json.loads(base64.b64decode(PAYLOAD))
backup=Path('/root/tolf-backups/ny-termination-20261024')
backup.mkdir(mode=0o700,exist_ok=True)
for name,text in files.items():
 p=Path(name);b=backup/name.lstrip('/')
 if p.exists() and not b.exists():b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,b)
 p.parent.mkdir(parents=True,exist_ok=True)
 target=p.with_name(p.name+'.termination-candidate') if name=='/etc/tolf-ny-relay.nft' else p
 target.write_text(text);target.chmod(0o755 if name.startswith('/usr/') or name.startswith('/etc/init.d/') else 0o600)
for name in files:
 if name.startswith('/usr/'):
  if 'python' in files[name].splitlines()[0]:compile(files[name],name,'exec')
  else:subprocess.run(['sh','-n',name],check=True)
subprocess.run(['/usr/sbin/ocserv','-t','-c','/etc/ocserv-ny-moscow/ocserv.conf'],check=True)
subprocess.run(['nft','-c','-f','/etc/tolf-ny-relay.nft.termination-candidate'],check=True)
print('Staged dedicated listener and validated configuration')
""".replace('PAYLOAD',repr(payload))
print(remote(apply))
for name,text in out.items():
 if name in ['/etc/ocserv-ny-moscow/ocserv.conf','/etc/init.d/ocserv-ny-moscow','/usr/libexec/tolf-oc-users']:
  (BASE/Path(name).name).write_text(text)
(BASE/'moscow-changes.json').write_text(json.dumps(out,indent=2))
