import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("bypass",ROOT/"setup/measurements/install-direct-bypass.py")
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
class BypassPolicy(unittest.TestCase):
 def test_preserve_and_narrow_exclusions(self):
  original=b"route = default\nno-route = 192.168.4.0/24\ndns = 10.254.0.53\n"
  patched=M.patched(original)
  self.assertTrue(patched.startswith(original))
  self.assertEqual(patched.count(b"no-route = "),4)
  for ip in M.IPS:self.assertIn(("no-route = "+ip+"/32\n").encode(),patched)
  self.assertEqual(M.patched(patched),patched)
 def test_global_scope(self):
  p=M.patched(b"route = default\n[vhost:private.example]\nroute = 10.0.0.0/8\n")
  self.assertLess(p.index(M.BEGIN.encode()),p.index(b"[vhost:"))
  self.assertIn(b"route = 10.0.0.0/8",p)
 def test_conflict_is_not_overwritten(self):
  with self.assertRaises(AssertionError):M.patched(b"append-global-routes = false\n")
 def test_modified_policy_is_not_overwritten(self):
  with self.assertRaises(AssertionError):M.patched((M.BLOCK.replace("/32","/24",1)).encode())
if __name__=="__main__":unittest.main()
