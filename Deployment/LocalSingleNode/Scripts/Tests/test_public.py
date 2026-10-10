"""Public configuration, isolated ingress and secret file contracts."""
import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

LIB = Path(__file__).resolve().parents[1] / "lib"
ROOT = LIB.parents[3]
sys.path.insert(0, str(LIB))
import public_config
import public_collisions
from ls_settings import settings

TUNNEL = "12345678-1234-1234-1234-123456789abc"
TOKEN = base64.b64encode(json.dumps({"a": "a" * 32, "t": TUNNEL, "s": "fixture-secret"}).encode()).decode()


class PublicTests(unittest.TestCase):
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
        self.assertIn("{{ deploy_root }}/cloudflared/", text)

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
