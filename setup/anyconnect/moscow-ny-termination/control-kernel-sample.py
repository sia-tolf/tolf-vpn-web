#!/usr/bin/python3
"""Bounded kernel IP sampling for a disposable, explicitly named control session."""
import os,sys,json,time,ctypes,struct,mmap,fcntl,collections
from pathlib import Path
import subprocess
cn,pid,seconds=sys.argv[1],int(sys.argv[2]),float(sys.argv[3])
assert cn.startswith('tolf-oc-') and cn!='tolf-oc-7c6f1f95ada34d0aa2d36d019a703264'
assert 0<seconds<=10
users=json.loads(subprocess.check_output(['occtl','-s','/var/run/occtl-ny-moscow.socket','-j','show','users']))
assert any(u.get('Username')==cn and int(u['ID'])==pid for u in users)
start=(Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()[19]
modules=[]
for line in Path('/proc/modules').read_text().splitlines():
 p=line.split()
 if len(p)>=6:
  base=int(p[5],16)
  if base:modules.append((base,base+int(p[1]),p[0]))
attr=bytearray(128)
struct.pack_into('IIQQQQQ',attr,0,1,128,0,5000000,1|32,0,1|16|64|(1<<22))
struct.pack_into('I',attr,48,1)
struct.pack_into('H',attr,108,32)
libc=ctypes.CDLL(None,use_errno=True)
buf=(ctypes.c_char*len(attr)).from_buffer(attr)
fd=libc.syscall(298,ctypes.byref(buf),pid,-1,-1,8)
if fd<0:raise OSError(ctypes.get_errno(),'perf_event_open')
ips=collections.Counter();stacks=collections.Counter();lost=0
try:
 page=os.sysconf('SC_PAGESIZE')
 ring=mmap.mmap(fd,page*17,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ|mmap.PROT_WRITE)
 offset,size=struct.unpack_from('QQ',ring,1040)
 if not offset:offset,size=page,page*16
 tail=struct.unpack_from('Q',ring,1032)[0]
 def take(pos,n):
  p=pos%size
  if p+n<=size:return ring[offset+p:offset+p+n]
  return ring[offset+p:offset+size]+ring[offset:offset+n-(size-p)]
 fcntl.ioctl(fd,0x2403,0);fcntl.ioctl(fd,0x2400,0)
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  time.sleep(.05)
  head=struct.unpack_from('Q',ring,1024)[0]
  while tail<head:
   typ,misc,n=struct.unpack('IHH',take(tail,8))
   if n<8 or n>size:raise RuntimeError('Invalid perf record')
   body=take(tail+8,n-8)
   if typ==9 and len(body)>=16:
    ips[struct.unpack_from('Q',body)[0]]+=1
    nr=struct.unpack_from('Q',body,8)[0]
    if nr<=512 and 16+nr*8<=len(body):stacks[tuple(struct.unpack_from(str(nr)+'Q',body,16))]+=1
   elif typ==2 and len(body)>=16:lost+=struct.unpack_from('Q',body,8)[0]
   tail+=n
  struct.pack_into('Q',ring,1032,tail)
 fcntl.ioctl(fd,0x2401,0)
 ring.close()
finally:os.close(fd)
counts=collections.Counter()
for ip,n in ips.items():
 name=next((name for lo,hi,name in modules if lo<=ip<hi),'core-or-unmapped')
 counts[name]+=n
(Path(__file__).parent/'samples.json').write_text(json.dumps({'ips':{hex(k):v for k,v in ips.items()},'moduleRanges':modules,'stacks':[[[hex(ip) for ip in stack],n] for stack,n in stacks.items()]}))
print(json.dumps({'samples':sum(ips.values()),'lost':lost,'modules':counts.most_common(),'distinctIPs':len(ips)}))
