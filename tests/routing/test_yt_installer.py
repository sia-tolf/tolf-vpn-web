import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "setup/routing/install-yt-routing.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("yt_installer", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class YtInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_installer()

    def test_embedded_openwrt_script_parses(self):
        subprocess.run(
            ["sh", "-n"],
            input=self.module.REMOTE_SCRIPT,
            text=True,
            check=True,
        )

    def test_uci_clone_emits_batch_set_commands(self):
        self.assertIn("sed 's/^/set /'", self.module.REMOTE_SCRIPT)

    def test_riga_nft_patch_is_idempotent(self):
        original = """#!/usr/sbin/nft -f
flush ruleset
table ip nat {
    chain postrouting {
        type nat hook postrouting priority 100;
        oifname "ens3" ip saddr { 10.17.0.0/24, 10.20.0.0/24 } masquerade
    }
}
table inet tolf_vpn_mss {
    chain forward {
        type filter hook forward priority -140; policy accept;
    }
}
"""
        patched = self.module.patch_riga_nft(original)
        self.assertIn("10.18.0.0/24", patched)
        self.assertIn("TOLF YT MSS v1", patched)
        self.assertEqual(self.module.patch_riga_nft(patched), patched)

    def test_mode_is_not_added_to_public_frontend(self):
        config = (ROOT / "js/config.js").read_text()
        self.assertNotIn("'yt'", config)
        self.assertNotIn('"yt"', config)
        self.assertNotIn("yt_domains4", config)

    def test_required_youtube_delivery_domains_are_present(self):
        script = self.module.REMOTE_SCRIPT
        for domain in ("youtube.com", "youtu.be", "googlevideo.com", "ytimg.com"):
            self.assertIn(domain, script)

    def test_atomic_restores_binary_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config"
            self.module.atomic(path, b"original\n", 0o600)
            self.assertEqual(path.read_bytes(), b"original\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
