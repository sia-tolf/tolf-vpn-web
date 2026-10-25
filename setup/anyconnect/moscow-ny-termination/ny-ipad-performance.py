#!/usr/bin/python3
"""Bounded metadata-only sampling for the authorized NY/Moscow iPad session."""
import os,json,time,re,subprocess
from pathlib import Path
CN='tolf-oc-7c6f1f95ada34d0aa2d36d019a703264'
SOCKET='/var/run/occtl-ny-moscow.socket'
OUT=Path('/root/tolf-diagnostics/ny-ipad-performance')
def users():
 if not Path(SOCKET).exists():return []
 r=subprocess.run(['occtl','-s',SOCKET,'--json','show','users'],capture_output=True,text=True,timeout=5,check=True)
 value=json.loads(r.stdout)
 if not isinstance(value,list):raise ValueError('Invalid session inventory')
 return value
def counter(dev,name):
 return int((Path('/sys/class/net')/dev/'statistics'/name).read_text())
def sample(u):
 pid=int(u['ID']);dev=u['Device']
 if not re.fullmatch(r'vpns-mowN[0-9]+',dev):raise ValueError('Unexpected interface')
 root=Path('/proc')/str(pid)
 stat=(root/'stat').read_text().rsplit(') ',1)[1].split()
 net=Path('/sys/class/net')/dev
 d={'at':time.time(),'pid':pid,'device':dev,'startTicks':int(stat[19]),
    'clockTicks':os.sysconf('SC_CLK_TCK'),'cpuTicks':int(stat[11])+int(stat[12]),
    'processor':int(stat[36]),'ifindex':int((net/'ifindex').read_text()),
    'queue':int((net/'tx_queue_len').read_text()),
    'txBytes':counter(dev,'tx_bytes'),'rxBytes':counter(dev,'rx_bytes'),
    'txPackets':counter(dev,'tx_packets'),'rxPackets':counter(dev,'rx_packets'),
    'txDropped':counter(dev,'tx_dropped'),'rxDropped':counter(dev,'rx_dropped')}
 inodes=set()
 for f in (root/'fd').iterdir():
  try:v=os.readlink(f)
  except OSError:continue
  if v.startswith('socket:['):inodes.add(v[8:-1])
 udp=[]
 for line in Path('/proc/net/udp').read_text().splitlines()[1:]:
  p=line.split()
  if len(p)>=13 and p[9] in inodes and p[2]!='00000000:0000':
   tx,rx=p[4].split(':')
   udp.append({'inode':p[9],'txQueue':int(tx,16),'rxQueue':int(rx,16),'drops':int(p[-1])})
 d['udp']=udp
 return d
def main():
 os.umask(0o077);OUT.mkdir(parents=True,mode=0o700,exist_ok=True)
 target=None;refresh=0;file=None;opened=0;previous=None
 while True:
  now=time.monotonic()
  if now>=refresh:
   try:target=next((u for u in users() if u.get('Username')==CN and u.get('State')=='connected'),None)
   except (OSError,ValueError,subprocess.SubprocessError):target=None
   refresh=now+5
  if target is None:
   if file:file.close();file=None
   previous=None;time.sleep(1);continue
  try:
   row=sample(target)
   identity=(row['pid'],row['startTicks'],row['ifindex'])
   if file is None or identity!=opened_identity or now-opened>=300:
    if file:file.close()
    name=OUT/('session-'+str(row['pid'])+'-'+str(time.time_ns())+'.jsonl')
    file=name.open('x');opened=now;opened_identity=identity
    for old in sorted(OUT.glob('session-*.jsonl'),key=lambda p:p.stat().st_mtime)[:-24]:
     old.unlink()
    previous=None
   if previous and previous['pid']==row['pid'] and previous['startTicks']==row['startTicks']:
    dt=row['at']-previous['at']
    if dt>0:
     row['corePercent']=round(100*(row['cpuTicks']-previous['cpuTicks'])/row['clockTicks']/dt,2)
     row['downloadMbps']=round((row['txBytes']-previous['txBytes'])*8/dt/1e6,3)
     row['uploadMbps']=round((row['rxBytes']-previous['rxBytes'])*8/dt/1e6,3)
     row['newTxDrops']=row['txDropped']-previous['txDropped']
     row['newRxDrops']=row['rxDropped']-previous['rxDropped']
   file.write(json.dumps(row,separators=(',',':'))+chr(10));file.flush()
   previous=row
   time.sleep(0.25 if max(row.get('downloadMbps',0),row.get('uploadMbps',0))>=10 else 1)
  except (OSError,ValueError,KeyError,ProcessLookupError):
   if file:file.close();file=None
   target=None;previous=None;refresh=0;time.sleep(1)
if __name__=='__main__':main()
