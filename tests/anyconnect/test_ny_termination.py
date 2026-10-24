import importlib.util,json,tempfile,unittest,types
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'setup/anyconnect/moscow-ny-termination'
snapshot=json.loads((BASE/'moscow-changes.json').read_text())
external=types.ModuleType('external')
exec(compile(snapshot['/usr/libexec/tolf-oc-external-exit'],'external','exec'),external.__dict__)
spec=importlib.util.spec_from_file_location('nodes',(BASE/'tolf_oc_nodes.py'))
nodes=importlib.util.module_from_spec(spec);spec.loader.exec_module(nodes)
CN='tolf-oc-'+'a'*32
class Routing(unittest.TestCase):
 def run_members(self,pool,mode,choice):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'run').mkdir();(root/'base/device-modes').mkdir(parents=True)
   (root/'run'/f'{CN}.123').write_text(pool)
   (root/'base/device-modes'/CN).write_text(mode)
   return external.members({CN:choice},runtime=root/'run',base=root/'base')
 def test_new_york_pool_always_exits_us(self):
  for mode in ['auto','ru','lv','yt']:
   for choice in ['riga','us','all_us']:
    with self.subTest(mode=mode,choice=choice):
     self.assertEqual(self.run_members('10.24.0.20',mode,choice),{'all':{'10.24.0.20'},'auto':set(),'yt':set()})
 def test_regular_moscow_unchanged(self):
  self.assertEqual(self.run_members('10.21.0.20','auto','riga')['all'],set())
  self.assertEqual(self.run_members('10.21.0.20','auto','us')['auto'],{'10.21.0.20'})
 def test_revoked_identity_is_not_routed(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'run').mkdir();(root/'base/device-modes').mkdir(parents=True)
   (root/'run'/f'{CN}.123').write_text('10.24.0.20')
   self.assertEqual(external.members({},runtime=root/'run',base=root/'base')['all'],set())
 def test_accounting_accepts_new_pool(self):
  m=types.ModuleType('accounting')
  exec(compile(snapshot['/usr/libexec/tolf-oc-nft-accounting'],'accounting','exec'),m.__dict__)
  with patch.dict(m.os.environ,{'REASON':'connect','USERNAME':CN,'ID':'123','IP_REMOTE':'10.24.0.20'}):
   self.assertEqual(m.env(),('connect',CN,'123','10.24.0.20'))
 def test_logical_new_york_session(self):
  class Fake:
   def __init__(self,entry):self.entry=entry
   def call(self,cmd):return {'username':CN,'connected':True,'entries':{'moscow':False,'us':True}}
   def session(self,cn):return False
  result=nodes.Nodes({k:Fake(k) for k in ['moscow','riga','us']}).sessions(CN)
  self.assertTrue(result['nodes']['us']['connected'])
  self.assertFalse(result['nodes']['moscow']['connected'])
  self.assertEqual(result['nodes']['us']['via'],'moscow')
if __name__=='__main__':unittest.main()
