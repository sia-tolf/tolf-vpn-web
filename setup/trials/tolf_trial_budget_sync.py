#!/usr/bin/python3
"""Root transport only; wallet SQLite work runs as the existing API service user."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

NODES={
 'riga':('188.214.39.114','/opt/tolf-mcp/riga_ed25519','/opt/tolf-api/.ssh/known_hosts'),
 'moscow':('92.243.66.204','/opt/tolf-mcp/moscow_ed25519','/opt/tolf-api/.ssh/known_hosts'),
 'us':('162.252.174.201','/opt/tolf-mcp/us_ed25519','/opt/tolf-api/node-keys/us_known_hosts')}
STATE=Path('/var/lib/tolf-api/trial-budget-delivery.json')
REMOTE='''import json,os,pathlib,sys,tempfile,subprocess,hashlib
data=json.load(sys.stdin)
assert data.get('version')==1
directory=pathlib.Path('/etc/tolf-trials');directory.mkdir(mode=0o700,exist_ok=True)
body=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
target=directory/'blocked.json'
if not target.exists() or target.read_bytes()!=body:
 fd,name=tempfile.mkstemp(dir=directory,prefix='.blocked-')
 with os.fdopen(fd,'wb') as f:f.write(body);f.flush();os.fsync(f.fileno())
 os.chmod(name,0o600);os.replace(name,target)
result=subprocess.run(['/usr/bin/python3','/usr/local/lib/tolf-trials/tolf_trial_access.py'],capture_output=True,text=True,timeout=35)
assert result.returncode==0,'trial_gate_not_confirmed'
status=json.loads(result.stdout)
assert status['manifestSha256']==hashlib.sha256(body).hexdigest()
print(json.dumps({'applied':True,'revision':status['manifestSha256']}))
'''


def send(name,config):
    host,key,known=NODES[name]
    argv=['/usr/bin/ssh','-T','-i',key,'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+known,'-o','ConnectTimeout=8','root@'+host,'/usr/bin/python3','-c',"'"+REMOTE.replace("'","'\"'\"'")+"'"]
    result=subprocess.run(argv,input=json.dumps(config),capture_output=True,text=True,timeout=48)
    if result.returncode:raise RuntimeError('node_not_confirmed')
    return json.loads(result.stdout)


def main():
    result=subprocess.run(['/usr/sbin/runuser','-u','tolfa','--','/opt/tolf-api/venv/bin/python','/opt/tolf-api/tolf_trial_packages.py','--snapshot'],capture_output=True,text=True,timeout=25)
    if result.returncode:raise RuntimeError('trial_wallet_snapshot_unavailable')
    view=json.loads(result.stdout)
    addresses=sorted({r[4][0] for r in socket.getaddrinfo('api.tolf.is',443,socket.AF_INET,socket.SOCK_STREAM)})
    config={'version':1,'principals':view['principals'],'allTrialPrincipals':view['allTrialPrincipals'],'validUntil':time.time()+90,'controlIPv4':addresses}
    status={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={name:pool.submit(send,name,config) for name in NODES}
        for name,job in jobs.items():
            try:status[name]=job.result()
            except Exception:status[name]={'applied':False}
    record={'at':time.time(),'trialAccounts':view['trialAccounts'],'exhaustedAccounts':view['exhaustedAccounts'],'nodes':status}
    STATE.write_text(json.dumps(record));STATE.chmod(0o600)
    print(json.dumps(record))
    if not all(v['applied'] for v in status.values()):raise SystemExit(1)


if __name__=='__main__':main()
