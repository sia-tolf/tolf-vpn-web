import importlib.util
import json
from pathlib import Path
import plistlib
import sys
import tempfile
import types
import unittest

sys.path.insert(0, "/opt/tolf-api")
CANDIDATE = Path(__file__).resolve().parents[2] / "setup/anyconnect/relay-api"
def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, CANDIDATE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
endpoint = load("tolf_oc_endpoint", "tolf_oc_endpoint.py")
sys.modules["tolf_oc_endpoint"] = endpoint
profile = load("relay_mobileconfig", "tolf_oc_mobileconfig.py")

class RelayTests(unittest.TestCase):
    def test_country_selection_and_stable_profile_identity(self):
        catalog = {"moscow":{"host":"oc.tolf.is:4443","name":"Moscow"},
                   "riga":{"host":"oc-riga.tolf.is:443","name":"Riga"},
                   "us":{"host":endpoint.DIRECT,"name":"New York"}}
        row = {"id":"7c6f1f95-ada3-4d0a-a2d3-6d019a703264","label":"Test"}
        authority = types.SimpleNamespace(bundle=lambda row:(b"dummy-p12", "test"))
        request = lambda ip:types.SimpleNamespace(client=types.SimpleNamespace(host=ip))
        with tempfile.TemporaryDirectory() as tmp:
            endpoint.CONFIG = Path(tmp)/"relay.json"
            endpoint.CONFIG.write_text(json.dumps({"enabled":True}))
            direct = endpoint.request_catalog(catalog, request("188.214.39.114"))
            relay = endpoint.request_catalog(catalog, request("176.226.199.30"))
            self.assertEqual(relay["us"]["host"],endpoint.RELAY)
            for ip in ["188.214.39.114","162.252.174.201","192.168.200.64",None]:
                self.assertEqual(endpoint.request_catalog(catalog,request(ip))["us"]["host"],endpoint.DIRECT)
            self.assertEqual(relay["moscow"],catalog["moscow"])
            self.assertEqual(relay["riga"],catalog["riga"])
            self.assertEqual(catalog["us"]["host"],endpoint.DIRECT)
            docs = [plistlib.loads(profile.make_combined_profile(row,authority,c["us"]["host"],"New York",production=True,catalog=c)) for c in [direct,relay]]
            self.assertEqual(docs[0]["PayloadUUID"],docs[1]["PayloadUUID"])
            self.assertEqual(docs[1]["PayloadDisplayName"],"TOLF New York AnyConnect")
            self.assertEqual(docs[1]["PayloadContent"][1]["VPN"]["RemoteAddress"],endpoint.RELAY)
            endpoint.CONFIG.write_text(json.dumps({"enabled":False}))
            self.assertEqual(endpoint.request_catalog(catalog,request("176.226.199.30"))["us"]["host"],endpoint.DIRECT)
            endpoint.CONFIG.write_text("broken")
            self.assertEqual(endpoint.request_catalog(catalog,request("176.226.199.30"))["us"]["host"],endpoint.DIRECT)

if __name__ == "__main__":
    unittest.main()
