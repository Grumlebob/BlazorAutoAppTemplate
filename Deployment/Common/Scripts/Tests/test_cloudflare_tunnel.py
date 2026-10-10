"""Offline Cloudflare resource ownership, retries and credential safeguards."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Component/lib"))
import cloudflare_tunnel as cf

ACCOUNT = "a" * 32
ZONE = "b" * 32
TUNNEL = "12345678-1234-1234-1234-123456789abc"
CONFIG = {"account_id": ACCOUNT, "zone_name": "example.com", "tunnel_name": "fixture-demo",
          "public_hostname": "demo.example.com", "origin_port": 8085}


class FakeApi:
    def __init__(self):
        self.tunnels = []
        self.records = []
        self.config = {}
        self.calls = []
        self.fail = None

    def listing(self, path, filters=None):
        if path == "/zones":
            return [{"id": ZONE, "account": {"id": ACCOUNT}, "status": "active"}]
        return copy.deepcopy(self.records if "dns_records" in path else self.tunnels)

    def get(self, path, allow_missing=False):
        if path.endswith("/token"):
            return "x" * 48
        return {"config": copy.deepcopy(self.config)}

    def request(self, method, path, body=None):
        self.calls.append((method, path, copy.deepcopy(body)))
        if self.fail == (method, "dns" if "dns_records" in path else "tunnel"):
            raise ValueError("ambiguous request")
        if method == "PUT":
            self.config = copy.deepcopy(body["config"])
            return {"result": {"config": self.config}}
        if "dns_records" in path:
            record = {"id": "c" * 32, **body}
            self.records.append(record)
            return {"result": record}
        tunnel = {"id": TUNNEL, "name": body["name"], "config_src": "cloudflare", "status": "inactive"}
        self.tunnels.append(tunnel)
        return {"result": tunnel}


class TunnelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state.json"
        self.token = self.root / "connector.token"
        self.api = FakeApi()

    def provisioner(self, config=None):
        return cf.Provisioner(self.api, config or CONFIG, self.state)

    def apply(self):
        return self.provisioner().reconcile(True, self.token)

    def test_create_check_and_repeat_do_not_duplicate_or_print_tokens(self):
        result = self.apply()
        self.assertEqual(TUNNEL, result["tunnel_id"])
        self.assertEqual(3, len(self.api.calls))
        self.assertEqual(0o600, self.state.stat().st_mode & 0o777)
        self.assertEqual(0o600, self.token.stat().st_mode & 0o777)
        self.assertNotIn(self.token.read_text().strip(), json.dumps(result))
        self.provisioner().reconcile()
        self.apply()
        self.assertEqual(3, len(self.api.calls))
        self.assertEqual(1, len(self.api.tunnels))
        self.assertEqual(1, len(self.api.records))

    def test_missing_check_never_mutates(self):
        with self.assertRaisesRegex(ValueError, "not provisioned"):
            self.provisioner().reconcile()
        self.assertEqual([], self.api.calls)
        self.assertFalse(self.state.exists())

    def test_refuse_foreign_tunnel_name(self):
        self.api.tunnels = [{"name": CONFIG["tunnel_name"], "id": TUNNEL}]
        with self.assertRaisesRegex(ValueError, "recorded ownership"):
            self.apply()
        self.assertEqual([], self.api.calls)

    def test_refuse_any_foreign_dns_record_before_creation(self):
        for record_type in ("A", "AAAA", "CNAME", "TXT"):
            self.api.records = [{"id": "c" * 32, "type": record_type, "name": CONFIG["public_hostname"]}]
            with self.assertRaisesRegex(ValueError, "DNS hostname already"):
                self.apply()
            self.assertEqual([], self.api.calls)

    def test_refuse_foreign_routes_without_overwrite(self):
        self.apply()
        count = len(self.api.calls)
        self.api.config["ingress"].insert(0, {"hostname": "other.example.com", "service": "http://127.0.0.1:9000"})
        with self.assertRaisesRegex(ValueError, "conflicting ingress"):
            self.apply()
        self.assertEqual(count, len(self.api.calls))

    def test_accept_cloudflare_empty_defaults_without_mutation(self):
        self.apply()
        self.api.config["warp-routing"] = {"enabled": False}
        self.api.config["originRequest"] = {}
        for entry in self.api.config["ingress"]:
            entry["originRequest"] = {}
        self.provisioner().reconcile()
        self.assertEqual(3, len(self.api.calls))

    def test_refuse_config_identity_changes(self):
        self.apply()
        with self.assertRaisesRegex(ValueError, "different configuration"):
            self.provisioner({**CONFIG, "public_hostname": "other.example.com"})

    def test_ambiguous_tunnel_creation_is_not_retried(self):
        self.api.fail = ("POST", "tunnel")
        with self.assertRaises(ValueError):
            self.apply()
        self.api.fail = None
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.apply()
        self.assertEqual(1, len(self.api.calls))
        self.assertEqual("create-tunnel", json.loads(self.state.read_text())["pending"])

    def test_ambiguous_dns_creation_is_not_retried(self):
        self.api.fail = ("POST", "dns")
        with self.assertRaises(ValueError):
            self.apply()
        self.api.fail = None
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.apply()
        self.assertEqual(3, len(self.api.calls))

    def test_interrupted_dns_response_can_be_recorded_without_new_post(self):
        self.apply()
        values = json.loads(self.state.read_text())
        values.pop("dns_id")
        values["pending"] = "create-dns"
        cf.private_write(self.state, json.dumps(values))
        self.apply()
        self.assertEqual("c" * 32, json.loads(self.state.read_text())["dns_id"])
        self.assertEqual(3, len(self.api.calls))

    def test_changed_dns_target_and_id_are_refused(self):
        self.apply()
        self.api.records[0]["content"] = "foreign.example.com"
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.apply()
        self.api.records[0]["content"] = TUNNEL + ".cfargotunnel.com"
        self.api.records[0]["id"] = "d" * 32
        with self.assertRaisesRegex(ValueError, "ID changed"):
            self.apply()

    def test_symlink_and_permissive_credential_files_are_refused(self):
        cf.private_write(self.token, "private")
        link = self.root / "link"
        link.symlink_to(self.token)
        with self.assertRaises(OSError):
            cf.protected_read(link)
        with self.assertRaises(ValueError):
            cf.private_write(link, "replacement")
        self.token.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "0600"):
            cf.protected_read(self.token)

    def test_hostname_port_and_account_validation(self):
        for key, value in (("public_hostname", "foreign.test"), ("public_hostname", "a..example.com"),
                           ("public_hostname", "*.example.com"), ("public_hostname", "Demo.example.com"),
                           ("origin_port", True), ("origin_port", 80), ("account_id", "../invalid")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                cf.validate_config({**CONFIG, key: value})

    def test_api_pagination_reads_all_pages(self):
        api = cf.Api("fixture")
        with patch.object(api, "request", side_effect=[
            {"result": [{"id": 1}], "result_info": {"total_pages": 2}},
            {"result": [{"id": 2}], "result_info": {"total_pages": 2}},
        ]) as request:
            self.assertEqual([{"id": 1}, {"id": 2}], api.listing("/zones"))
            self.assertIn("page=2", request.call_args_list[1].args[1])

    def test_cli_errors_never_dump_credential_content(self):
        config = self.root / "config.json"
        config.write_text(json.dumps(CONFIG))
        cf.private_write(self.token, "SECRET_SENTINEL")
        with patch("sys.stderr", new_callable=io.StringIO) as output:
            self.assertEqual(1, cf.main(["--config", str(config), "--token-file", str(self.token), "--state", str(self.state)]))
            self.assertNotIn("SECRET_SENTINEL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
