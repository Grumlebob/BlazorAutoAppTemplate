"""Public configuration, isolated ingress and secret file contracts."""
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

LIB = Path(__file__).resolve().parents[1] / "lib"
ROOT = LIB.parents[3]
sys.path.insert(0, str(LIB))
import public_config
import readiness
import public_collisions
from ls_settings import settings

TUNNEL = "12345678-1234-1234-1234-123456789abc"
TOKEN = base64.b64encode(json.dumps({"a": "a" * 32, "t": TUNNEL, "s": "fixture-secret"}).encode()).decode()


class PublicTests(unittest.TestCase):
    def test_readiness_identifies_probe_to_cloudflare(self):
        request = readiness.build_request("https://demo.example.com/health/ready")
        self.assertEqual(
            "BlazorAutoApp-Deployment-Readiness/1.0",
            request.get_header("User-agent"),
        )

    def test_lan_only_defaults_stay_disabled(self):
        self.assertEqual({"public_enabled": False}, public_config.validate("", "", 8085, "", settings()))

    def test_token_matches_configured_tunnel(self):
        values = public_config.validate("demo.example.com", TUNNEL, 8085, TOKEN, settings())
        self.assertTrue(values["public_enabled"])
        self.assertEqual("2026.10.0", values["public_cloudflared_version"])
        self.assertTrue(values["public_cloudflared_checksum"].startswith("sha256:"))

    def test_token_accepts_base64url_alphabet(self):
        token = None
        for codepoint in range(0xA0, 0xD800):
            payload = json.dumps(
                {"a": "a" * 32, "t": TUNNEL, "s": chr(codepoint)}, ensure_ascii=False
            ).encode()
            if "+" in base64.b64encode(payload).decode() or "/" in base64.b64encode(payload).decode():
                token = base64.urlsafe_b64encode(payload).decode().rstrip("=")
                break
        self.assertIsNotNone(token)
        self.assertTrue(public_config.validate("demo.example.com", TUNNEL, 8085, token, settings())["public_enabled"])

    def test_missing_mismatched_or_unsafe_inputs_fail(self):
        for host, tunnel, port, token in [
            ("", TUNNEL, 8085, TOKEN), ("demo.example.com", TUNNEL, 80, TOKEN),
            ("demo.example.com", TUNNEL, 8080, TOKEN), ("demo.example.com", TUNNEL, 8085, ""),
            ("demo.example.com", "22345678-1234-1234-1234-123456789abc", 8085, TOKEN),
            ("demo.example.com/path", TUNNEL, 8085, TOKEN),
            ("Demo.example.com", TUNNEL, 8085, TOKEN), ("*.example.com", TUNNEL, 8085, TOKEN),
        ]:
            with self.subTest(host=host, port=port), self.assertRaises(ValueError):
                public_config.validate(host, tunnel, port, token, settings())

    def test_public_ingress_is_loopback_and_https_forwarded(self):
        text = (ROOT / "Deployment/LocalSingleNode/ansible/roles/single_node_public/templates/app.caddy.j2").read_text()
        self.assertIn("bind 127.0.0.1", text)
        self.assertIn("header_up X-Forwarded-Proto https", text)
        self.assertIn("http://:{{ public_origin_port }}", text)
        self.assertIn("header_up X-Forwarded-Host {{ public_hostname }}", text)
        self.assertNotIn("trusted_proxies", text)
        self.assertIn("Cf-Connecting-Ip", text)

    def test_service_does_not_use_shared_binary_or_command_line_token(self):
        text = (ROOT / "Deployment/LocalSingleNode/ansible/roles/single_node_public/templates/cloudflared.service.j2").read_text()
        self.assertIn("DynamicUser=yes", text)
        self.assertIn("LoadCredential=tunnel-token:", text)
        self.assertIn("--token-file %d/tunnel-token", text)
        self.assertNotIn("--token ", text)
        self.assertIn("/usr/local/libexec/cloudflared-{{ app_name }}/{{ public_cloudflared_version }}/cloudflared", text)
        self.assertNotIn("{{ deploy_root }}", text)
        tasks = (ROOT / "Deployment/LocalSingleNode/ansible/roles/single_node_public/tasks/main.yml").read_text()
        self.assertIn('path: "/usr/local/libexec/cloudflared-{{ app_name }}"', tasks)
        self.assertIn('mode: "0755"', tasks)
        self.assertIn("--property=ActiveState,SubState,ExecMainStatus", tasks)
        self.assertIn("retries: 12", tasks)
        self.assertIn("delay: 5", tasks)
        self.assertIn("'ActiveState=active'", tasks)
        self.assertIn("'SubState=running'", tasks)
        self.assertIn("'ExecMainStatus=0'", tasks)

    def test_unowned_executable_path_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exec_base = root / "usr/local/libexec"
            foreign_path = exec_base / "cloudflared-books" / "2026.10.0"
            foreign_path.mkdir(parents=True)
            with patch.object(public_collisions, "ETC", root / "etc"), \
                 patch.object(public_collisions, "PUBLIC_EXEC_BASE", exec_base), \
                 patch.object(public_collisions, "settings", return_value={"app_name": "books"}), \
                 patch.object(public_collisions, "command", return_value=""):
                with self.assertRaisesRegex(ValueError, "exists without verified ownership"):
                    public_collisions.check(
                        "https://example.test/repo", "demo.example.com", TUNNEL, 8085, "2026.10.0"
                    )

    def test_shared_executable_parent_must_be_traversable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exec_base = root / "usr/local/libexec"
            exec_base.mkdir(parents=True)
            exec_base.chmod(0o750)
            with patch.object(public_collisions, "ETC", root / "etc"), \
                 patch.object(public_collisions, "PUBLIC_EXEC_BASE", exec_base), \
                 patch.object(public_collisions, "settings", return_value={"app_name": "books"}), \
                 patch.object(public_collisions, "command", return_value=""):
                with self.assertRaisesRegex(ValueError, "parent is not traversable"):
                    public_collisions.check(
                        "https://example.test/repo", "demo.example.com", TUNNEL, 8085, "2026.10.0"
                    )

    def test_unrecorded_executable_version_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            etc = root / "etc"
            exec_base = root / "usr/local/libexec"
            (exec_base / "cloudflared-books" / "2026.10.0").mkdir(parents=True)
            state_dir = etc / "books"
            state_dir.mkdir(parents=True)
            (state_dir / "public.json").write_text(json.dumps({
                "source_repo_url": "https://example.test/repo", "hostname": "demo.example.com",
                "tunnel_id": TUNNEL, "origin_port": 8085,
            }))
            with patch.object(public_collisions, "ETC", etc), \
                 patch.object(public_collisions, "PUBLIC_EXEC_BASE", exec_base), \
                 patch.object(public_collisions, "settings", return_value={"app_name": "books"}), \
                 patch.object(public_collisions, "command", return_value=""):
                with self.assertRaisesRegex(ValueError, "exists without verified ownership"):
                    public_collisions.check(
                        "https://example.test/repo", "demo.example.com", TUNNEL, 8085, "2026.10.0"
                    )

    def test_owned_executable_path_can_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            etc = root / "etc"
            exec_base = root / "usr/local/libexec"
            owned_path = exec_base / "cloudflared-books" / "2026.10.0"
            owned_path.mkdir(parents=True)
            source = "https://example.test/repo"
            state_dir = etc / "books"
            state_dir.mkdir(parents=True)
            (state_dir / "public.json").write_text(json.dumps({
                "source_repo_url": source, "hostname": "demo.example.com", "tunnel_id": TUNNEL,
                "origin_port": 8085, "cloudflared_version": "2026.10.0",
            }))
            with patch.object(public_collisions, "ETC", etc), \
                 patch.object(public_collisions, "PUBLIC_EXEC_BASE", exec_base), \
                 patch.object(public_collisions, "settings", return_value={"app_name": "books"}), \
                 patch.object(public_collisions, "command", return_value=""):
                public_collisions.check(source, "demo.example.com", TUNNEL, 8085, "2026.10.0")

    def test_public_and_lan_acceptance_each_run_once(self):
        lane = (LIB.parent / "acceptance-check.sh").read_text()
        public = (LIB.parent / "public-acceptance-check.sh").read_text()
        self.assertEqual(1, lane.count("Scripts/Test-DeployedSite.ps1"))
        self.assertEqual(1, public.count("Scripts/Test-DeployedSite.ps1"))
        self.assertIn("public-acceptance-check.sh", lane)
        self.assertIn('-BaseUrl "$PUBLIC_URL"', public)
        self.assertIn("lib/readiness.py", public)


if __name__ == "__main__":
    unittest.main()
