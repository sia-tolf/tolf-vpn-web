"""Run against a staged or installed IKEv2 module; never issue real profiles."""
import importlib.util,os,plistlib,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,"/opt/tolf-api")
source=Path(os.environ.get("TOLF_PROFILES_SOURCE","/opt/tolf-api/tolf_profiles.py"))
if not source.exists():
    raise unittest.SkipTest("TOLF profile service module is not installed")
spec=importlib.util.spec_from_file_location("profile_names_candidate",source)
profiles=importlib.util.module_from_spec(spec);spec.loader.exec_module(profiles)

class ProfileNames(unittest.TestCase):
    def test_all_entries_routes_languages_and_legacy_names(self):
        identity={"PROFILE_UUID":"00000000-0000-4000-8000-000000000001","VPN_UUID":"00000000-0000-4000-8000-000000000002",
                  "PROFILE_IDENTIFIER":"is.tolf.test.profile","VPN_IDENTIFIER":"is.tolf.test.vpn"}
        for server,city in [("moscow","Moscow"),("riga","Riga"),("us","New York")]:
            for route in profiles.ROUTING[server]:
                for language in ["ru","lv","en"]:
                    for requested in ["","TOLF "+city,"TOLF "+city+(" "+route if route else ""),"TOLF "+city+" IKEv2","TOLF "+city+" IKEv2 "+route]:
                        expected="TOLF "+city+" IKEv2 "+("AUTO" if server=="riga" and route=="sr" else (route or "auto").upper())
                        name,data=profiles._build_profile("synthetic-user","synthetic-password",server,route,"ios",identity,
                                                         {"profileName":requested,"language":language})
                        p=plistlib.loads(data);vpn=p["PayloadContent"][0]
                        self.assertEqual(name,expected)
                        self.assertEqual(p["PayloadDisplayName"],expected)
                        self.assertEqual(vpn["UserDefinedName"],expected)
                        self.assertEqual(vpn["PayloadDisplayName"],expected)
                        self.assertEqual(vpn["VPNType"],"IKEv2")
                        self.assertEqual(vpn["IKEv2"].get("LocalIdentifier"),route)
                        self.assertEqual(vpn["IKEv2"]["RemoteAddress"],profiles.HOSTS[server])
                        self.assertEqual(p["PayloadUUID"],identity["PROFILE_UUID"])
                        self.assertEqual(vpn["PayloadUUID"],identity["VPN_UUID"])
    def test_install_action_translations(self):
        for language,label in [("ru","Установить профиль"),("lv","Instalēt profilu"),("en","Install profile")]:
            metadata={"platform":"ios","profile":"TOLF New York IKEv2","language":language}
            with patch.object(profiles,"_load",return_value=(metadata,b"",".mobileconfig","application/x-apple-aspen-config")):
                text=profiles.page("synthetic-token").body.decode()
            self.assertIn('>'+label+'</a>',text)
            self.assertNotIn("Download Mobile Config",text)
            self.assertIn("TOLF New York IKEv2",text)

if __name__=="__main__":unittest.main()
