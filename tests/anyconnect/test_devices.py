import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ONE = "tolf-oc-" + "1" * 32
TWO = "tolf-oc-" + "2" * 32


class DeviceControl(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        self.rules = self.dir / "rules"
        self.connections = self.dir / "connections"
        for name, text in {
            "nft": '#!/bin/sh\ncase "$1" in list) exit 1 ;; -c) exit "${TOLF_TEST_NFT_FAIL:-0}" ;; -f) cat "$2" > "$TOLF_TEST_RULES" ;; *) exit 1 ;; esac\n',
            "conntrack": '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TOLF_TEST_CONNECTIONS"\n',
            "occtl": '#!/bin/sh\ncase "$*" in *"show user "*) exit 2 ;; *) exit 0 ;; esac\n',
        }.items():
            path = self.bin / name
            path.write_text(text)
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + ":" + os.environ["PATH"],
                        TOLF_OC_DIRECTORY=str(self.dir), TOLF_OC_DEVICE_RUNTIME=str(self.dir / "runtime"),
                        TOLF_OC_DEVICE_LOCK=str(self.dir / "lock"), TOLF_TEST_RULES=str(self.rules),
                        TOLF_TEST_CONNECTIONS=str(self.connections))

    def tearDown(self):
        self.temp.cleanup()

    def run_device(self, *args, **environment):
        return subprocess.run(["sh", str(ROOT / "setup/anyconnect/moscow-devices.sh"), *args],
                              env=dict(self.env, **environment), capture_output=True, text=True)

    def hook(self, cn, ip, reason="connect", identity="123"):
        return self.run_device("hook", USERNAME=cn, IP_REMOTE=ip, REASON=reason, ID=identity)

    def test_two_devices_have_independent_modes_and_only_target_flows_clear(self):
        self.assertEqual(self.run_device("set", ONE, "auto").returncode, 0)
        self.assertEqual(self.run_device("set", TWO, "lv").returncode, 0)
        self.assertEqual(self.hook(ONE, "10.21.0.10").returncode, 0)
        self.assertEqual(self.hook(TWO, "10.23.0.11", identity="124").returncode, 0)
        result = self.run_device("set", ONE, "ru")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "ru")
        rules = self.rules.read_text()
        self.assertIn("tolf_oc_device_ru { 10.21.0.10 }", rules)
        self.assertIn("tolf_oc_device_lv { 10.23.0.11 }", rules)
        self.assertEqual(self.connections.read_text().splitlines(), ["-D -f ipv4 -s 10.21.0.10"])

    def test_unregistered_device_and_untrusted_input_are_rejected(self):
        self.assertNotEqual(self.hook(ONE, "10.21.0.10").returncode, 0)
        for cn in ("../../escape", ONE + ";id", "tolf-oc-" + "A" * 32, "pilot-tolf"):
            self.assertNotEqual(self.run_device("set", cn, "auto").returncode, 0)
        self.assertEqual(self.run_device("set", ONE, "auto").returncode, 0)
        for ip in ("192.168.0.2", "10.21.0.1", "10.21.0.255", "10.21.0.10;id", "10.21.0.001", "10.21.0.extra.10"):
            self.assertNotEqual(self.hook(ONE, ip).returncode, 0)

    def test_pilot_remains_separate_and_reused_lease_is_removed(self):
        self.assertEqual(self.run_device("set", ONE, "yt").returncode, 0)
        self.assertEqual(self.hook(ONE, "10.21.0.10").returncode, 0)
        self.assertEqual(self.hook("pilot-tolf", "10.21.0.10", identity="124").returncode, 0)
        self.assertNotIn("add element", self.rules.read_text())
        self.assertEqual(self.run_device("pilot-clear").returncode, 0)
        self.assertEqual(self.connections.read_text().strip(), "-D -f ipv4 -s 10.21.0.10")

    def test_policy_failure_restores_mode_and_disconnect_cleans_lease(self):
        self.assertEqual(self.run_device("set", ONE, "auto").returncode, 0)
        self.env["TOLF_TEST_NFT_FAIL"] = "1"
        self.assertNotEqual(self.run_device("set", ONE, "lv").returncode, 0)
        self.assertEqual((self.dir / "device-modes" / ONE).read_text().strip(), "auto")
        self.env["TOLF_TEST_NFT_FAIL"] = "0"
        self.assertEqual(self.hook(ONE, "10.22.0.10").returncode, 0)
        self.assertEqual(self.hook(ONE, "10.22.0.10", reason="disconnect").returncode, 0)
        self.assertNotIn("add element", self.rules.read_text())

    def test_remove_denies_live_ip_and_blocks_reconnection(self):
        self.assertEqual(self.run_device("set", ONE, "ru").returncode, 0)
        self.assertEqual(self.hook(ONE, "10.21.0.10").returncode, 0)
        result = self.run_device("remove", ONE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["removed"])
        self.assertIn("tolf_oc_device_deny { 10.21.0.10 }", self.rules.read_text())
        self.assertNotEqual(self.hook(ONE, "10.21.0.10", identity="124").returncode, 0)

    def test_remote_wrapper_rejects_shell_syntax_and_unknown_commands(self):
        helper = self.dir / "helper"
        helper.write_text('#!/bin/sh\nprintf "%s\\n" "$*"\n')
        helper.chmod(0o755)
        wrapper = self.dir / "remote"
        wrapper.write_text((ROOT / "setup/anyconnect/moscow-remote.sh").read_text().replace(
            "/usr/libexec/tolf-oc-devices", str(helper)))
        for command in ("id", "tolf-oc-device " + ONE + " auto;id", "tolf-oc-session " + ONE + "\nid", "tolf-oc-device " + ONE + " auto extra"):
            result = subprocess.run(["sh", str(wrapper)], env=dict(self.env, SSH_ORIGINAL_COMMAND=command), capture_output=True)
            self.assertNotEqual(result.returncode, 0)
        result = subprocess.run(["sh", str(wrapper)], env=dict(self.env, SSH_ORIGINAL_COMMAND="tolf-oc-device " + ONE + " yt"), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "set " + ONE + " yt")


if __name__ == "__main__":
    unittest.main()
