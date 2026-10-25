#!/usr/bin/env python3
"""Extend the existing numeric-suffix TUN queue policy to the NY listener."""
from pathlib import Path
import shutil,subprocess
p=Path('/usr/libexec/tolf-ocserv/tun-queue-policy')
backup=Path('/root/tolf-backups/ny-termination-20261024/tun-queue-policy.before-ny-prefix')
s=p.read_text()
old='    vpns-mow*) suffix="${device#vpns-mow}" ;;'
new='    vpns-mowN*) suffix="${device#vpns-mowN}" ;;'
if new not in s:
 assert s.count(old)==1, 'Unexpected queue policy; manual review required'
 if not backup.exists():shutil.copy2(p,backup)
 p.write_text(s.replace(old,new+'\n'+old))
subprocess.run(['/bin/sh','-n',str(p)],check=True)
for entry in Path('/sys/class/net').glob('vpns-mowN*'):
 suffix=entry.name.removeprefix('vpns-mowN')
 if suffix.isdecimal() and (entry/'tun_flags').exists():
  subprocess.run([str(p),'connect',entry.name],check=True)
  assert (entry/'tx_queue_len').read_text().strip()=='2000'
print('NY listener queue policy validated')
