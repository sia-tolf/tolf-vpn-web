#!/opt/tolf-api/venv/bin/python
"""Install verified production credentials without printing them or issuing an order."""
import getpass
import grp
import hmac
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
sys.path.insert(0,'/opt/tolf-api')
import tolf_billing_live as live

def main():
 if os.geteuid()!=0:
  raise SystemExit('Run as root.')
 access=getpass.getpass('Montonio LIVE Access Key (hidden): ').strip()
 secret=getpass.getpass('Montonio LIVE Secret Key (hidden): ').strip()
 if not access or not secret:raise SystemExit('Both keys are required. Nothing changed.')
 sandbox=json.loads(Path('/etc/tolf-payments/montonio-sandbox.json').read_text())
 if hmac.compare_digest(access,sandbox['accessKey']) or hmac.compare_digest(secret,sandbox['secretKey']):
  raise SystemExit('Sandbox keys cannot be used for LIVE. Nothing changed.')
 target=Path('/etc/tolf-payments/montonio-live.json')
 cfg={'environment':'production','apiBase':live.BASE,'enabled':True,'accessKey':access,'secretKey':secret,'storeUuid':str(uuid.uuid4())}
 fd,path=tempfile.mkstemp(prefix='.live-verify-',dir=target.parent)
 staged=Path(path)
 try:
  with os.fdopen(fd,'w') as f:json.dump(cfg,f);f.flush();os.fsync(f.fileno())
  live.CONFIG=staged
  response=live.provider('GET','/stores/payment-methods')
  cfg['storeUuid']=str(uuid.UUID(response['uuid']))
  if not isinstance(response.get('paymentMethods'),dict) or not response['paymentMethods']:
   raise ValueError()
  staged.write_text(json.dumps(cfg)+'\n');os.chown(staged,0,grp.getgrnam('tolfa').gr_gid);os.chmod(staged,0o640)
  with staged.open('rb') as f:os.fsync(f.fileno())
  os.replace(staged,target)
  print('LIVE keys verified and installed. Live payments are available only to administrators. No order or charge was created.')
 except Exception:
  raise SystemExit('LIVE verification failed. Existing configuration was not changed. Check the production keys and payment methods in Montonio.') from None
 finally:
  if staged.exists():staged.unlink()
if __name__=='__main__':main()
