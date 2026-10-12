"""Parity checks for the shared LocalCluster and Cloud settings rules."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
COMMON_LIB = ROOT / "Deployment/Common/Scripts/Component/lib"
sys.path.insert(0, str(COMMON_LIB))
import settings_validation as shared  # noqa: E402


def load_settings_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOCAL_CLUSTER = load_settings_module(
    "deploy_settings_under_test",
    "Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py",
)
CLOUD = load_settings_module(
    "cloud_settings_under_test",
    "Deployment/Cloud/Scripts/Component/lib/cloud_settings.py",
)


def valid_values(target: str) -> dict[str, str]:
    values = {
        "app_name": "books",
        "app_port": "8085",
        "postgres_port": "5432",
        "redis_port": "6379",
        "public_hostname": "books.example.com",
        "deploy_root": "/opt/books",
        "cloudflare_tunnel_name": "books",
        "cloudflared_version": "2026.5.0",
    }
    if target == "Cloud":
        values.update(
            {
                "cloud_private_network_cidr": "10.70.0.0/24",
                "cloud_private_gateway_ip": "10.70.0.1",
                "cloud_main_private_ip": "10.70.0.2",
                "cloud_app1_private_ip": "10.70.0.3",
                "cloud_app2_private_ip": "10.70.0.4",
                "cloud_db_private_ip": "10.70.0.5",
            }
        )
    return values


class SettingsValidationTests(unittest.TestCase):
    def test_both_targets_accept_valid_settings_and_blank_optional_values(self):
        for name, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
            with self.subTest(target=name):
                values = valid_values(name)
                values.update(
                    {
                        "observability_enabled": "",
                        "observability_root": "",
                        "observability_grafana_port": "",
                        "observability_prometheus_retention_time": "",
                    }
                )
                self.assertEqual([], module.validate(values))

        local_defaults = LOCAL_CLUSTER.apply_defaults(valid_values("LocalCluster"))
        self.assertEqual("node-main-books", local_defaults["runner_name"])
        self.assertEqual("localcluster-books", local_defaults["runner_label"])
        self.assertEqual("", local_defaults["inventory_dns_suffix"])

    def test_observability_ports_keep_boundaries_collisions_and_error_order(self):
        expected = [
            "app_port must be between 1024 and 65535",
            "observability_grafana_port must be between 1024 and 65535",
            "observability_grafana_port must not reuse app_port (1023)",
            "observability_alertmanager_port must be between 1024 and 65535",
            "observability_prometheus_port must be between 1024 and 65535",
            "observability_prometheus_port must not reuse observability_alertmanager_port (65536)",
            "observability_loki_port must be a number",
        ]
        for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
            values = valid_values(target)
            values.update(
                {
                    "app_port": "1023",
                    "observability_grafana_port": "1023",
                    "observability_alertmanager_port": "65536",
                    "observability_prometheus_port": "65536",
                    "observability_loki_port": "not-a-port",
                    "observability_tempo_http_port": "65535",
                    "observability_tempo_otlp_grpc_port": "1024",
                }
            )
            with self.subTest(target=target):
                self.assertEqual(expected, module.validate(values))

    def test_port_helper_reads_existing_owners_without_mutating_input(self):
        owners = {8085: "app_port"}
        errors = shared.validate_observability_ports(
            {"observability_grafana_port": "8085", "observability_loki_port": "9200"},
            ["observability_grafana_port", "observability_loki_port"],
            owners,
        )
        self.assertEqual(["observability_grafana_port must not reuse app_port (8085)"], errors)
        self.assertEqual({8085: "app_port"}, owners)

    def test_retention_predicates_keep_existing_syntax(self):
        for value in ("24h", "7d", "4w", "12m", "1y", "24h\n"):
            with self.subTest(period=value):
                self.assertTrue(shared.valid_retention_period(value))
        for value in ("24H", "7 days", "", "1.5h"):
            with self.subTest(period=value):
                self.assertFalse(shared.valid_retention_period(value))

        for value in ("512MB", "4GB", "6GB"):
            with self.subTest(size=value):
                self.assertTrue(shared.valid_retention_size(value))
        for value in ("512mb", "4 TB", "GB", ""):
            with self.subTest(size=value):
                self.assertFalse(shared.valid_retention_size(value))

        expected = {
            "LocalCluster": [
                "observability_prometheus_retention_time must look like 24h, 7d, 4w, 12m, or 1y",
                "observability_loki_retention_period must look like 24h, 7d, 4w, 12m, or 1y",
                "observability_prometheus_retention_size must look like 512MB or 6GB",
            ],
            "Cloud": [
                "observability_prometheus_retention_time must look like 24h, 7d, 4w, 12m, or 1y",
                "observability_loki_retention_period must look like 24h, 7d, 4w, 12m, or 1y",
                "observability_prometheus_retention_size must look like 512MB or 4GB",
            ],
        }
        for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
            values = valid_values(target)
            values.update(
                {
                    "observability_prometheus_retention_time": "24H",
                    "observability_loki_retention_period": "7 days",
                    "observability_tempo_retention_period": "1y",
                    "observability_prometheus_retention_size": "512mb",
                }
            )
            with self.subTest(target=target):
                self.assertEqual(expected[target], module.validate(values))

    def test_dns_rules_and_target_specific_hostname_errors_are_preserved(self):
        for value in ("books.example.com", "books.example.com.", "A.example.com"):
            with self.subTest(hostname=value):
                self.assertTrue(shared.valid_dns_name(value))
        for value in (
            "localhost",
            "-bad.example.com",
            "bad-.example.com",
            f"{'a' * 64}.example.com",
            f"{'a' * 250}.example",
        ):
            with self.subTest(hostname=value):
                self.assertFalse(shared.valid_dns_name(value))

        expected = {
            "LocalCluster": "public_hostname must be a DNS hostname inside your Cloudflare zone, for example books.example.com",
            "Cloud": "public_hostname must be a DNS hostname inside your Cloudflare zone",
        }
        for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
            values = valid_values(target)
            values["public_hostname"] = "-bad.example.com"
            with self.subTest(target=target):
                self.assertEqual([expected[target]], module.validate(values))

    def test_shared_posix_path_checks_preserve_existing_predicates(self):
        self.assertEqual((True, True, True), shared.posix_opt_path_checks("/opt/books"))
        self.assertEqual((False, False, False), shared.posix_opt_path_checks("relative path"))
        self.assertEqual((True, False, False), shared.posix_opt_path_checks("/opt/metrics dashboard"))

    def test_target_specific_path_examples_and_error_order_are_preserved(self):
        expected = {
            "LocalCluster": [
                "observability_root must be under /opt, for example /opt/books-observability",
                "observability_root must not contain whitespace",
                "observability_root must contain only letters, numbers, dots, underscores, hyphens, and slashes",
                "deploy_root must be under /opt, for example /opt/books",
            ],
            "Cloud": [
                "observability_root must be under /opt, for example /opt/bookscloud-observability",
                "observability_root must not contain whitespace",
                "observability_root must contain only letters, numbers, dots, underscores, hyphens, and slashes",
                "deploy_root must be under /opt, for example /opt/bookscloud",
            ],
        }
        for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
            values = valid_values(target)
            values["observability_root"] = "/srv/metrics dashboard"
            values["deploy_root"] = "/srv/books"
            with self.subTest(target=target):
                self.assertEqual(expected[target], module.validate(values))

    def test_cloud_private_network_rejections_remain_target_specific(self):
        values = valid_values("Cloud")
        values.update(
            {
                "cloud_private_gateway_ip": "10.71.0.1",
                "cloud_app2_private_ip": "10.70.0.3",
                "cloud_db_private_ip": "2001:db8::1",
            }
        )
        self.assertEqual(
            [
                "cloud_private_gateway_ip must be inside 10.70.0.0/24",
                "cloud_db_private_ip must be an IPv4 address",
                "cloud_app2_private_ip must not reuse cloud_app1_private_ip (10.70.0.3)",
            ],
            CLOUD.validate(values),
        )

    def test_both_validator_clis_work_from_repository_and_unrelated_directories(self):
        fixture_values = {
            "LocalCluster": valid_values("LocalCluster"),
            "Cloud": valid_values("Cloud"),
        }
        scripts = {
            "LocalCluster": ROOT / "Deployment/LocalCluster/Scripts/Component/lib/validate-deploy-settings.py",
            "Cloud": ROOT / "Deployment/Cloud/Scripts/Component/lib/validate-cloud-settings.py",
        }

        with tempfile.TemporaryDirectory() as temp_root:
            temp = Path(temp_root)
            unrelated_cwd = temp / "unrelated-working-directory"
            unrelated_cwd.mkdir()
            fixtures = {}
            for target, values in fixture_values.items():
                fixture = temp / f"{target.lower()}-settings.yml"
                fixture.write_text("".join(f"{key}: {value}\n" for key, value in values.items()), encoding="utf-8")
                fixtures[target] = fixture.resolve()

            for target in ("LocalCluster", "Cloud"):
                for cwd in (ROOT, unrelated_cwd):
                    with self.subTest(target=target, cwd=cwd):
                        result = subprocess.run(
                            [sys.executable, str(scripts[target].resolve()), "--settings", str(fixtures[target])],
                            cwd=cwd,
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                        self.assertIn("settings are valid", result.stdout)


if __name__ == "__main__":
    unittest.main()
