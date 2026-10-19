#!/usr/bin/python3
"""Dedicated NY measurement certificate relay. Certificate/key never enter logs."""
import argparse,fcntl,hashlib,json,os,pathlib,shlex,subprocess,time
BASE=pathlib.Path(__file__).resolve().parent
RIGA=['/usr/bin/ssh','-F','/dev/null','-T','-i','/opt/tolf-mcp/riga_ed25519','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/opt/tolf-api/.ssh/known_hosts','-o','ConnectTimeout=10','root@188.214.39.114']
US=['/usr/bin/ssh','-F','/dev/null','-T','-i','/opt/tolf-mcp/us_ed25519','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/opt/tolf-mcp/us_known_hosts','-o','ConnectTimeout=10','root@162.252.174.201']
GET=r"""
import json
from pathlib import Path
p=Path('/etc/letsencrypt/live/tolf-speedtest-us-vpn')
print(json.dumps({'cert':(p/'fullchain.pem').read_text(),'key':(p/'privkey.pem').read_text()}))
"""
APPLY=r"""
import json,sys,pathlib,subprocess,hashlib,os,time,ssl,socket,http.client
data=json.load(sys.stdin)
UNIT=pathlib.Path('/etc/systemd/system/tolf-vpn-measurement.service')
CONF=pathlib.Path('/etc/tolf-vpn-measurement.toml')
CERT=pathlib.Path('/etc/tolf-node/pki/measurement-vpn-chain.pem')
KEY=pathlib.Path('/etc/tolf-node/pki/measurement-vpn.key')
STATE=pathlib.Path('/var/lib/tolf-measurements/private-us-20261019/state.json')
HOST='speedtest-us.vpn.tolf.is'
def run(*a):return subprocess.run(a,check=True,capture_output=True,text=True,timeout=30)
def sha(d):return hashlib.sha256(d).hexdigest()
def write(p,content,mode):
 p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_suffix(p.suffix+'.tolf-new');t.write_text(content);t.chmod(mode);t.replace(p)
addresses=json.loads(run('ip','-j','addr','show').stdout)
assert any(a.get('local')=='162.252.174.201' for d in addresses for a in d.get('addr_info',[])),'Unexpected host'
assert pathlib.Path('/usr/local/bin/tolf-speedtest-backend').is_file(),'Backend missing'
vpn_before=run('systemctl','show','ocserv','--property=MainPID','--value').stdout.strip()
public_before=run('systemctl','show','tolf-measurement','--property=MainPID','--value').stdout.strip()
if STATE.exists():
 state=json.loads(STATE.read_text());assert state['owner']=='tolf-us-vpn-measurement-20261019'
else:
 assert data['install'],'Initial installation is not authorized by this invocation'
 assert not any(p.exists() for p in [UNIT,CONF,CERT,KEY]),'Unexpected existing target file'
 state={'owner':'tolf-us-vpn-measurement-20261019','status':'installing'}
 STATE.parent.mkdir(parents=True,exist_ok=True);STATE.write_text(json.dumps(state));STATE.chmod(0o600)
assert not UNIT.exists() or UNIT.read_text()==data['unit'],'Service configuration changed'
assert not CONF.exists() or CONF.read_text()==data['config'],'Backend configuration changed'
new_digest=sha((data['cert']+data['key']).encode())
old_digest=sha(CERT.read_bytes()+KEY.read_bytes()) if CERT.exists() and KEY.exists() else None
changed=new_digest!=old_digest
if changed:
 write(CERT,data['cert'],0o644);write(KEY,data['key'],0o600)
run('openssl','x509','-in',str(CERT),'-noout','-checkhost',HOST,'-checkend','604800')
cert_pub=run('openssl','x509','-in',str(CERT),'-noout','-pubkey').stdout
key_pub=run('openssl','pkey','-in',str(KEY),'-pubout').stdout
assert cert_pub==key_pub,'Certificate key mismatch'
if data['install']:
 write(UNIT,data['unit'],0o644);write(CONF,data['config'],0o644)
 run('systemd-analyze','verify',str(UNIT))
 run('systemctl','daemon-reload');run('systemctl','enable','--now','tolf-vpn-measurement.service')
elif changed:run('systemctl','try-restart','tolf-vpn-measurement.service')
run('systemctl','is-active','tolf-vpn-measurement.service')
class Connection(http.client.HTTPSConnection):
 def connect(self):
  self.sock=self._context.wrap_socket(socket.create_connection(('10.250.81.1',8444),timeout=8),server_hostname=HOST)
def request(method,path,body=None):
 c=Connection(HOST,8444,context=ssl.create_default_context(),timeout=10)
 c.request(method,path,body=body,headers={'Origin':'https://vpn.tolf.is'})
 r=c.getresponse();payload=r.read();status=r.status;cors=r.getheader('Access-Control-Allow-Origin');c.close()
 assert status==200 and cors in ('*','https://vpn.tolf.is'),'HTTPS/CORS health failed'
 return len(payload)
# The backend may need a moment after systemd reports the process started.
for i in range(20):
 try:
  assert request('GET','/empty.php?cors=true')==0
  break
 except (ConnectionError,OSError):
  time.sleep(.2)
else:raise RuntimeError('Private listener startup timed out')
assert request('GET','/garbage.php?cors=true&ckSize=1')==1048576,'Download length mismatch'
assert request('POST','/empty.php?cors=true',b'x'*65536)==0,'Upload confirmation failed'
assert run('systemctl','show','ocserv','--property=MainPID','--value').stdout.strip()==vpn_before,'VPN process changed'
assert run('systemctl','show','tolf-measurement','--property=MainPID','--value').stdout.strip()==public_before,'Public measurement process changed'
state.update({'status':'active','hostname':HOST,'address':'10.250.81.1','port':8444,'certificate_sha256':sha(data['cert'].encode()),'time':time.time(),'vpn_pid':int(vpn_before),'public_measurement_pid':int(public_before)})
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'status':'active','certificate_updated':changed,'trusted_tls':True,'cors':True,'download_bytes':1048576,'confirmed_upload_bytes':65536,'vpn_pid_unchanged':True,'public_measurement_pid_unchanged':True,'certificate_sha256':state['certificate_sha256']}))
"""
def remote(host,code,payload=None,timeout=90):
 r=subprocess.run(host+['python3 -c '+shlex.quote(code)],input=json.dumps(payload) if payload is not None else None,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError('Remote '+('issuer' if host is RIGA else 'measurement')+' operation failed (exit '+str(r.returncode)+'); sensitive output withheld')
 return json.loads(r.stdout)
p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--install',action='store_true');g.add_argument('--sync',action='store_true');a=p.parse_args()
os.umask(0o077)
lockdir=pathlib.Path('/run/tolf-us-measurement-cert-sync');lockdir.mkdir(exist_ok=True)
with (lockdir/'lock').open('w') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 material=remote(RIGA,GET)
 material.update({'install':a.install,'unit':(BASE/'tolf-vpn-measurement.service').read_text(),'config':(BASE/'tolf-vpn-measurement.toml').read_text()})
 result=remote(US,APPLY,material)
 state=pathlib.Path('/var/lib/tolf-us-measurement-cert-sync');state.mkdir(exist_ok=True)
 (state/'status.json').write_text(json.dumps(dict(result,time=time.time()),indent=2))
 print(json.dumps(result))
