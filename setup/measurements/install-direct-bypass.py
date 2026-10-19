#!/usr/bin/python3
"""Manage only the three public measurement split-exclude routes on TOLF ocserv nodes."""
import argparse,hashlib,json,pathlib,re,shlex,subprocess,time
IPS=['188.214.39.114','92.243.66.32','162.252.174.201']
BEGIN='# BEGIN TOLF DIRECT MEASUREMENT BYPASS 20261019'
END='# END TOLF DIRECT MEASUREMENT BYPASS 20261019'
BLOCK=BEGIN+'\n'+''.join('no-route = '+ip+'/32\n' for ip in IPS)+'append-global-routes = true\n'+END+'\n'
NODES={
 'riga':{'host':'188.214.39.114','key':'/opt/tolf-mcp/riga_ed25519','known':'/opt/tolf-api/.ssh/known_hosts','config':'/etc/ocserv/ocserv.conf','socket':'/var/run/occtl.socket','ctl':'/usr/bin/occtl','backup':'/var/lib/tolf-measurements/direct-bypass-20261019/ocserv.conf.before'},
 'moscow':{'host':'92.243.66.204','key':'/opt/tolf-mcp/moscow_ed25519','known':'/opt/tolf-api/.ssh/known_hosts','config':'/etc/ocserv-moscow/ocserv.conf','socket':'/var/run/occtl-moscow.socket','ctl':'/usr/bin/occtl','backup':'/root/tolf-direct-measurements-20261019/ocserv.conf.before'},
 'us':{'host':'162.252.174.201','key':'/opt/tolf-mcp/us_ed25519','known':'/opt/tolf-mcp/us_known_hosts','config':'/etc/ocserv/ocserv.conf','socket':'/run/occtl-node.socket','ctl':'/usr/bin/occtl','backup':'/var/lib/tolf-measurements/direct-bypass-20261019/ocserv.conf.before'}}
def sha(data):return hashlib.sha256(data).hexdigest()
def remote(node,script,data=None):
 n=NODES[node];cmd=['/usr/bin/ssh','-F','/dev/null','-T','-i',n['key'],'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+n['known'],'-o','ConnectTimeout=10','root@'+n['host'],'/bin/sh -c '+shlex.quote(script)]
 r=subprocess.run(cmd,input=data,capture_output=True,timeout=40)
 if r.returncode:raise RuntimeError(node+' operation failed exit='+str(r.returncode)+'; configuration/diagnostic output withheld')
 return r.stdout
def patched(data):
 s=data.decode()
 if BEGIN in s:
  assert s.count(BEGIN)==s.count(END)==1,'Malformed managed block'
  assert s[s.index(BEGIN):s.index(END)+len(END)]+'\n'==BLOCK,'Managed policy changed'
  return data
 # Preserve existing routes/exclusions. The current deployment uses full-tunnel defaults.
 existing=re.findall(r'(?m)^\s*append-global-routes\s*=\s*(\S+)',s)
 assert not existing or existing==['true'],'Conflicting global route merge setting'
 first_section=re.search(r'(?m)^\s*\[',s)
 if first_section:
  pos=first_section.start()
  return (s[:pos].rstrip()+'\n\n'+BLOCK+'\n'+s[pos:]).encode()
 return (s.rstrip()+'\n\n'+BLOCK).encode()
def prepare(node):
 n=NODES[node];old=remote(node,'cat '+shlex.quote(n['config']));new=patched(old)
 return old,new
def mode(node,cfg):
 permissions=remote(node,'ls -ldL '+cfg).decode().split()[0][1:10]
 assert len(permissions)==9
 bits=0
 for i,char in enumerate(permissions):
  if char in 'rwxst':bits|=1<<(8-i)
 return format(bits & 0o777,'o')
def apply(node,old,new):
 n=NODES[node];cfg=shlex.quote(n['config']);backup=shlex.quote(n['backup']);temp=shlex.quote(n['config']+'.tolf-direct-20261019.new')
 # Candidate is validated before changing the running configuration.
 script='set -e\numask 077\ncat > '+temp+'\n/usr/sbin/ocserv --test-config --config '+temp+'\n'
 remote(node,script,new)
 current=remote(node,'cat '+cfg)
 if sha(current)!=sha(old):raise RuntimeError(node+' configuration changed during preparation')
 script='set -e\numask 077\nmkdir -p '+shlex.quote(str(pathlib.PurePosixPath(n['backup']).parent))+'\nif [ ! -e '+backup+' ]; then cp -p '+cfg+' '+backup+'; fi\nchmod '+mode(node,cfg)+' '+temp+'\nmv '+temp+' '+cfg+'\n'
 remote(node,script)
 try:remote(node,shlex.quote(n['ctl'])+' -s '+shlex.quote(n['socket'])+' reload')
 except BaseException:
  remote(node,'cp -p '+backup+' '+cfg+'\n'+shlex.quote(n['ctl'])+' -s '+shlex.quote(n['socket'])+' reload')
  raise
 check=remote(node,'cat '+cfg);assert check==new
 return {'node':node,'status':'applied','config_sha256':sha(new),'exclusions':[ip+'/32' for ip in IPS],'reload_only':True,'clients_need_reconnect':True}
def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--node',choices=list(NODES),action='append');a=p.parse_args()
 names=a.node or list(NODES);prepared={name:prepare(name) for name in names};results=[]
 for name,(old,new) in prepared.items():
  if old==new:results.append({'node':name,'status':'already_configured'})
  elif a.apply:results.append(apply(name,old,new))
  else:results.append({'node':name,'status':'preflight_pass','changes_needed':True,'exclusions':[ip+'/32' for ip in IPS],'reload_only':True})
 print(json.dumps({'time':time.time(),'results':results}))
if __name__=='__main__':main()
