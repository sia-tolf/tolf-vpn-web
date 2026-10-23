import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "setup" / "anyconnect"))
import tolf_oc_shortcuts as shortcuts
import tolf_oc_mobileconfig as profiles
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

SIGNED = b"AEA1" + b"x" * 2200

class CiscoShortcuts(unittest.TestCase):
    def test_names_and_actions(self):
        for city in ("Москва", "Рига"):
            row = {"label": "iPhone <&> " + "😀" * 40}
            name = shortcuts.vpn_name(row, city)
            self.assertEqual(name, "TOLF " + {"Москва":"Moscow", "Рига":"Riga"}[city] + " AnyConnect")
            for mode in ("on", "off"):
                workflow = plistlib.loads(plistlib.dumps(shortcuts.workflow(name, mode)))
                action = workflow["WFWorkflowActions"][0]
                self.assertEqual(action["WFWorkflowActionIdentifier"],
                                 "com.cisco.anyconnect." + ("StartVpnIntent" if mode == "on" else "StopVpnIntent"))
                self.assertEqual(action["WFWorkflowActionParameters"], {"vpnConfig": name} if mode == "on" else {})
                self.assertEqual(workflow["WFWorkflowName"], "TOLF " + mode.upper())
                self.assertEqual(workflow["WFWorkflowImportQuestions"], [])

    def test_profile_names_are_english_for_all_entry_languages(self):
        cases = {
            "Moscow": ["Москва", "Maskava", "Moscow", "moscow"],
            "Riga": ["Рига", "Rīga", "Riga", "riga"],
            "New York": ["Нью-Йорк", "Ņujorka", "New York", "us", "new-york"],
        }
        for expected, aliases in cases.items():
            for city in aliases:
                with self.subTest(city=city):
                    name=shortcuts.vpn_name({"label":"iPad пользователя"},city)
                    self.assertEqual(name,"TOLF "+expected+" AnyConnect")
                    self.assertTrue(name.isascii())
                    start=shortcuts.workflow(name,"on")["WFWorkflowActions"][0]
                    self.assertEqual(start["WFWorkflowActionParameters"]["vpnConfig"],name)

    def test_controller_matches_distributed_template(self):
        # The distributed file and API must carry the same controller.
        path = Path(__file__).resolve().parents[2] / "shortcuts/auto-install/TOLF.plist"
        native = plistlib.loads(path.read_bytes())
        candidate = shortcuts.controller("TOLF Москва iPhone", "ru")
        self.assertEqual(candidate["WFWorkflowIcon"]["WFWorkflowIconStartColor"], 4282601983)
        native["WFWorkflowIcon"]["WFWorkflowIconStartColor"] = 4282601983
        self.assertEqual(candidate, native)
        for city in ("Москва", "Рига"):
            name = shortcuts.vpn_name({"label":"Phone <&>"}, city)
            document = shortcuts.controller(name)
            starts = [a for a in document["WFWorkflowActions"]
                      if a["WFWorkflowActionIdentifier"].endswith(".StartVpnIntent")]
            self.assertEqual(len(starts), 1)
            self.assertTrue(all(a["WFWorkflowActionParameters"] == {"vpnConfig":name, "ShowWhenRun":False} for a in starts))
            self.assertEqual(document["WFWorkflowName"], name)

    def test_menu_and_vpn_actions_are_profile_scoped(self):
        for name in ("TOLF Москва iPhone", "TOLF Рига iPad"):
            actions = shortcuts.controller(name)["WFWorkflowActions"]
            self.assertEqual(actions[0]["WFWorkflowActionIdentifier"], "is.workflow.actions.choosefrommenu")
            city = name.split(" ", 2)[1]
            self.assertEqual(name, actions[0]["WFWorkflowActionParameters"]["WFMenuPrompt"])
            native = [a["WFWorkflowActionParameters"] for a in actions if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.vpn.set"]
            self.assertEqual([p["WFVPNOperation"] for p in native], ["Set On Demand", "Set On Demand", "Disconnect"])
            self.assertEqual([p["WFOnDemandValue"] for p in native[:2]], [1, 0])
            for p in native:
                self.assertEqual(p["WFVPN"]["title"], name)
                self.assertNotIn("identifier", p["WFVPN"])
            self.assertFalse(any(a["WFWorkflowActionIdentifier"] == "com.cisco.anyconnect.StopVpnIntent" for a in actions))
            self.assertFalse(any(a["WFWorkflowActionIdentifier"] == "is.workflow.actions.conditional" for a in actions))
            for i, a in enumerate(actions):
                if a["WFWorkflowActionIdentifier"] == "com.cisco.anyconnect.StartVpnIntent":
                    self.assertEqual(actions[i-1]["WFWorkflowActionParameters"]["WFOnDemandValue"], 1)
                    self.assertIs(a["WFWorkflowActionParameters"]["ShowWhenRun"], False)

    def test_controller_clears_output_and_returns_home_after_all_branches(self):
        actions = shortcuts.controller("TOLF Москва iPhone")["WFWorkflowActions"]
        self.assertEqual([a["WFWorkflowActionIdentifier"] for a in actions[-3:]], [
            "is.workflow.actions.nothing",
            "is.workflow.actions.returntohomescreen",
            "is.workflow.actions.nothing"])
        depth = 0
        for action in actions[:-3]:
            params = action["WFWorkflowActionParameters"]
            if "WFControlFlowMode" in params:
                mode = params["WFControlFlowMode"]
                depth += 1 if mode == 0 else -1 if mode == 2 else 0
                self.assertGreaterEqual(depth, 0)
        self.assertEqual(depth, 0)

    def test_city_artifacts_keep_english_menu_and_binding(self):
        for city in ("Moscow", "Riga"):
            name = "TOLF " + city
            for lang, action in (("en", "🟢 Turn VPN on"),):
                path = Path(__file__).resolve().parents[2] / "shortcuts/cities" / lang / (name + ".plist")
                artifact = plistlib.loads(path.read_bytes())
                doc = shortcuts.controller(name)
                self.assertEqual(artifact["WFWorkflowActions"], doc["WFWorkflowActions"])
                self.assertEqual(doc["WFWorkflowName"], name)
                self.assertEqual(doc["WFWorkflowActions"][0]["WFWorkflowActionParameters"]["WFMenuPrompt"], name)
                self.assertTrue(doc["WFWorkflowActions"][0]["WFWorkflowActionParameters"]["WFMenuItems"][0]["WFValue"].startswith(action))
                self.assertTrue(shortcuts.valid_signed(path.with_suffix(".shortcut").read_bytes()))
                for item in doc["WFWorkflowActions"]:
                    params = item["WFWorkflowActionParameters"]
                    if "WFVPN" in params:
                        self.assertEqual(params["WFVPN"]["title"], name)

    def test_cache_reuses_signature_and_changes_with_name(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(shortcuts, "sign", return_value=SIGNED) as signer:
                shortcuts.signed_shortcut("TOLF Москва iPhone", "on", directory)
                shortcuts.signed_shortcut("TOLF Москва iPhone", "on", directory)
                self.assertEqual(signer.call_count, 1)
                shortcuts.signed_shortcut("TOLF Рига iPhone", "on", directory)
                self.assertEqual(signer.call_count, 2)
                shortcuts.signed_shortcut("TOLF Москва iPhone", "off", directory)
                shortcuts.signed_shortcut("TOLF Рига iPhone", "off", directory)
                self.assertEqual(signer.call_count, 3)

    def test_invalid_signing_response_is_not_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                shortcuts.signed_shortcut("TOLF Москва iPhone", "on", directory, lambda *_: b"error")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_route_authorization_and_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            app = FastAPI()
            def auth(request):
                if request.headers.get("x-test-user") != "owner":
                    raise HTTPException(401)
                return "owner"
            def record(user, device, active):
                if device != "mine":
                    raise HTTPException(404)
                return {"label": "iPhone"}
            profiles.register_combined_test(app, auth, record, None, str(Path(directory)/"test.db"), {"moscow", "riga"})
            client = TestClient(app)
            with patch.object(shortcuts, "signed_shortcut", return_value=SIGNED) as signer:
                path = "/oc/access/devices/mine/shortcuts/control.shortcut"
                self.assertEqual(client.get(path).status_code, 401)
                self.assertEqual(client.get(path.replace("mine", "other"), headers={"x-test-user":"owner"}).status_code, 404)
                self.assertFalse(signer.called)
                response = client.get(path+"?ingress=riga", headers={"x-test-user":"owner"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, SIGNED)
                self.assertEqual('inline; filename="TOLF Riga AnyConnect.shortcut"', response.headers["content-disposition"])
                self.assertEqual("application/x-apple-shortcut", response.headers["content-type"])
                signer.assert_called_once_with("TOLF Riga AnyConnect", "control")
                self.assertIn("no-store", response.headers["cache-control"])
                self.assertEqual(client.get(path+"?ingress=invalid", headers={"x-test-user":"owner"}).status_code, 400)
                self.assertEqual(client.get(path.replace("control.shortcut","bad.shortcut"), headers={"x-test-user":"owner"}).status_code, 400)
            with patch.object(shortcuts, "signed_shortcut", side_effect=ValueError("private details")):
                response = client.get(path, headers={"x-test-user":"owner"})
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("private details", response.text)

if __name__ == "__main__":
    unittest.main()
