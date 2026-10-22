from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase

import yaml

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import docker_gc  # noqa: E402

NOW = datetime(2026, 10, 23, 1, 2, 3, tzinfo=timezone.utc)
POLICY = docker_gc.desired_policy("10GB", "30GB", "30%")


class FakeNode:
    """Records commands and answers like a quiet node whose containers recover after a restart."""

    def __init__(self, containers=None, validate_ok=True, recover=True, build_running=False):
        self.containers = containers if containers is not None else {
            "app-web-1": ("no", "app"), "app-postgres-1": ("yes", "app"), "other-web-1": ("no", "other")}
        self.validate_ok = validate_ok
        self.recover = recover
        self.build_running = build_running
        self.calls = []
        self.restarts = 0

    def __call__(self, *args, timeout=120, check=True):
        self.calls.append(args)
        out, code = "", 0
        if args[:2] == ("dockerd", "--validate"):
            out, code = ("configuration OK", 0) if self.validate_ok else ("invalid builder.gc", 1)
        elif args[:2] == ("docker", "ps"):
            out = "\n".join(self.containers)
        elif args[:3] == ("docker", "inspect", "-f") and "Config.Labels" in args[3]:
            health, project = self.containers[args[4]]
            out = f"/{args[4]}|{health}|{project or '<no value>'}"
        elif args[:3] == ("docker", "inspect", "-f"):
            name = args[4]
            healthy = self.recover or self.restarts > 1
            status = "running" if healthy else "restarting"
            out = f"{status}|{'healthy' if self.containers[name][0] == 'yes' and healthy else ''}"
        elif args[:2] == ("pgrep", "-af"):
            out, code = ("1234 docker buildx build ." if self.build_running else "", 0 if self.build_running else 1)
        elif args[:3] == ("systemctl", "restart", "docker"):
            self.restarts += 1
        elif args[:2] == ("docker", "info"):
            out = "29.9.1"
        elif args[:3] == ("docker", "system", "df"):
            out = "Build Cache: 68GB (reclaimable 29GB)"
        result = subprocess.CompletedProcess(args, code, out, "")
        if check and code:
            raise docker_gc.GcError(f"{args} failed")
        return result


class DockerGcTests(TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.config = self.dir / "daemon.json"
        self.out = []

    def apply(self, node, **kwargs):
        return docker_gc.apply(self.config, POLICY, node, self.out.append, sleep=lambda _: None, now=NOW, **kwargs)

    def test_absent_config_is_created_with_only_the_gc_keys_and_an_absent_marker_backup(self):
        node = FakeNode()
        self.assertEqual(0, self.apply(node))
        self.assertEqual({"builder": {"gc": POLICY}}, json.loads(self.config.read_text()))
        marker = self.dir / "daemon.json.bak-20261023T010203Z.absent"
        self.assertTrue(marker.exists())
        self.assertEqual(1, node.restarts)

    def test_unrelated_settings_and_builder_keys_are_preserved(self):
        self.config.write_text(json.dumps({"log-driver": "local", "builder": {"features": {"x": True}, "gc": {"policy": []}}}))
        os.chmod(self.config, 0o640)
        self.apply(FakeNode())
        merged = json.loads(self.config.read_text())
        self.assertEqual("local", merged["log-driver"])
        self.assertEqual({"x": True}, merged["builder"]["features"])
        self.assertEqual([], merged["builder"]["gc"]["policy"])
        for key, value in POLICY.items():
            self.assertEqual(value, merged["builder"]["gc"][key])
        if os.name != "nt":
            self.assertEqual(0o640, self.config.stat().st_mode & 0o777)
        backup = self.dir / "daemon.json.bak-20261023T010203Z"
        self.assertEqual({"log-driver": "local", "builder": {"features": {"x": True}, "gc": {"policy": []}}},
                         json.loads(backup.read_text()))

    def test_already_applied_policy_is_a_no_op_without_restart(self):
        self.config.write_text(json.dumps({"builder": {"gc": POLICY}}))
        node = FakeNode()
        self.assertEqual(0, self.apply(node))
        self.assertEqual(0, node.restarts)
        self.assertFalse(list(self.dir.glob("daemon.json.bak-*")))

    def test_dry_run_validates_but_never_writes_or_restarts(self):
        node = FakeNode()
        self.assertEqual(0, self.apply(node, dry_run=True))
        self.assertFalse(self.config.exists())
        self.assertEqual(0, node.restarts)
        self.assertTrue(any(call[:2] == ("dockerd", "--validate") for call in node.calls))

    def test_invalid_json_and_incompatible_shapes_are_refused(self):
        self.config.write_text("{not json")
        with self.assertRaises(docker_gc.GcError):
            self.apply(FakeNode())
        self.config.write_text(json.dumps({"builder": "classic"}))
        with self.assertRaises(docker_gc.GcError):
            self.apply(FakeNode())
        self.config.write_text(json.dumps({"builder": {"gc": {"defaultKeepStorage": "20GB"}}}))
        with self.assertRaises(docker_gc.GcError):
            self.apply(FakeNode())

    def test_validation_failure_leaves_the_file_untouched(self):
        self.config.write_text(json.dumps({"log-driver": "local"}))
        node = FakeNode(validate_ok=False)
        with self.assertRaises(docker_gc.GcError):
            self.apply(node)
        self.assertEqual({"log-driver": "local"}, json.loads(self.config.read_text()))
        self.assertEqual(0, node.restarts)
        self.assertEqual(["daemon.json"], sorted(p.name for p in self.dir.iterdir()))

    def test_busy_node_is_refused_before_any_change(self):
        for node in (FakeNode(build_running=True),
                     FakeNode(containers={"app-web-1": ("no", "app"), "testcontainers-pg": ("yes", "")})):
            with self.assertRaises(docker_gc.GcError):
                self.apply(node)
            self.assertFalse(self.config.exists())
            self.assertEqual(0, node.restarts)

    def test_failed_recovery_restores_the_previous_file_and_restarts_again(self):
        original = json.dumps({"log-driver": "local"})
        self.config.write_text(original)
        node = FakeNode(recover=False)
        times = iter(range(0, 10_000, 400))
        real = docker_gc.time.monotonic
        docker_gc.time.monotonic = lambda: next(times)
        try:
            with self.assertRaises(docker_gc.GcError):
                self.apply(node)
        finally:
            docker_gc.time.monotonic = real
        self.assertEqual(original, self.config.read_text())
        self.assertEqual(2, node.restarts)

    def test_rollback_restores_the_exact_backup_or_removes_a_created_file(self):
        self.config.write_text(json.dumps({"log-driver": "local"}))
        self.apply(FakeNode())
        backup = self.dir / "daemon.json.bak-20261023T010203Z"
        node = FakeNode()
        docker_gc.rollback(self.config, backup, node, self.out.append, sleep=lambda _: None)
        self.assertEqual({"log-driver": "local"}, json.loads(self.config.read_text()))
        self.assertEqual(1, node.restarts)

        self.config.unlink()
        for leftover in self.dir.glob("daemon.json.bak-*"):
            leftover.unlink()
        self.apply(FakeNode())
        marker = self.dir / "daemon.json.bak-20261023T010203Z.absent"
        docker_gc.rollback(self.config, marker, FakeNode(), self.out.append, sleep=lambda _: None)
        self.assertFalse(self.config.exists())

    def test_rollback_refuses_unexpected_backup_files(self):
        stray = self.dir / "other.json"
        stray.write_text("{}")
        with self.assertRaises(docker_gc.GcError):
            docker_gc.rollback(self.config, stray, FakeNode(), self.out.append, sleep=lambda _: None)
        with self.assertRaises(docker_gc.GcError):
            docker_gc.rollback(self.config, self.dir / "daemon.json.bak-missing", FakeNode(), self.out.append,
                               sleep=lambda _: None)

    def test_policy_values_are_bounded(self):
        for args in (("0GB", "30GB", "30%"), ("10GB", "lots", "30%"), ("10GB", "30GB", "95%"), ("10GB", "30GB", "0%")):
            with self.assertRaises(docker_gc.GcError):
                docker_gc.desired_policy(*args)

    def test_no_command_ever_prunes_or_removes_docker_resources(self):
        node = FakeNode()
        self.apply(node)
        docker_gc.rollback(self.config, self.dir / "daemon.json.bak-20261023T010203Z.absent", node, self.out.append,
                           sleep=lambda _: None)
        for call in node.calls:
            joined = " ".join(call)
            for word in ("prune", " rm", "rmi", "volume", "kill", "stop"):
                self.assertNotIn(word, joined)

    def test_workflow_applies_only_on_main_behind_the_gate_and_lock(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/localsinglenode-docker-gc.yml").read_text())
        self.assertEqual(["workflow_dispatch"], list(workflow[True]))
        self.assertEqual("report", workflow[True]["workflow_dispatch"]["inputs"]["mode"]["default"])
        steps = workflow["jobs"]["docker-gc"]["steps"]
        names = [step.get("name") for step in steps]
        for required in ("Verify the intended native node", "Require main branch",
                         "Require green main CI for unchanged operation code"):
            self.assertLess(names.index(required), names.index("Apply the BuildKit GC policy under the shared deployment lock"))
        apply = next(step for step in steps if step.get("name") == "Apply the BuildKit GC policy under the shared deployment lock")
        self.assertEqual("inputs.mode == 'apply'", apply["if"])
        self.assertIn("with-deploy-lock.sh sudo -n python3 Deployment/LocalSingleNode/Scripts/lib/docker_gc.py apply", apply["run"])
