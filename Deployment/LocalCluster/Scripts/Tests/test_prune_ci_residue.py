#!/usr/bin/env python3
"""Behavioral mutation guards, with fake Docker/GitHub; no live deletions."""

import copy
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("GITHUB_REPOSITORY", "example/repo")

SPEC = importlib.util.spec_from_file_location(
    "cleaner", Path(__file__).resolve().parents[1] / "prune-ci-residue.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.cleaner = module.Cleaner(True, 25, "sample")
        self.created = self.cleaner.now - timedelta(days=3)
        self.item = {
            "Id": "a" * 64,
            "Created": self.created.isoformat(),
            "Labels": {
                module.PREFIX + "repository": module.REPOSITORY,
                module.PREFIX + "owner": "ci-smoke",
                module.PREFIX + "run_id": "123",
                module.PREFIX + "run_attempt": "1",
                module.PREFIX + "session": "123-1",
                module.PREFIX + "purpose": "smoke",
                module.PREFIX + "created_at": self.created.isoformat(),
            },
            "Mounts": [{"Type": "tmpfs", "Destination": "/data"}],
            "State": "exited",
            "Restart": "no",
            "Privileged": False,
        }
        self.run = {
            "id": 123,
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "path": ".github/workflows/ci.yml",
            "head_repository": {"full_name": module.REPOSITORY},
            "created_at": (self.created - timedelta(minutes=1)).isoformat(),
            "updated_at": (self.created + timedelta(hours=1)).isoformat(),
        }
        self.calls = []
        patch.object(module, "require_lock").start()
        self.api = patch.object(self.cleaner, "attempt", return_value=self.run).start()
        self.inspection = patch.object(
            self.cleaner, "inspect", side_effect=lambda *_: copy.deepcopy(self.item)
        ).start()
        self.command = patch.object(
            self.cleaner, "command", side_effect=self.fake_command
        ).start()
        self.addCleanup(patch.stopall)

    def fake_command(self, *args):
        self.calls.append(args)
        if args[:3] == ("docker", "container", "stop"):
            self.item["State"] = "exited"
        if args[:2] == ("docker", "info"):
            return "/var/lib/docker"
        if args[:3] == ("docker", "ps", "-aq"):
            return ""
        return ""

    def mutations(self):
        return [
            args for args in self.calls if len(args) > 2 and args[2] in ("stop", "rm")
        ]

    def test_dry_run_does_not_mutate(self):
        self.cleaner.apply = False
        self.cleaner.consider("container", self.item)
        self.assertEqual([], self.mutations())
        self.assertEqual(1, self.cleaner.counts["eligible"])

    def test_old_owned_stopped_container_removed_by_exact_id_without_force(self):
        self.cleaner.consider("container", self.item)
        self.assertEqual([("docker", "container", "rm", "a" * 64)], self.mutations())
        self.assertTrue(self.api.call_args.args[2])

    def test_running_ephemeral_container_stopped_then_removed(self):
        self.item["State"] = "running"
        self.cleaner.consider("container", copy.deepcopy(self.item))
        self.assertEqual(["stop", "rm"], [args[2] for args in self.mutations()])

    def test_foreign_local_missing_or_compose_labels_protected(self):
        for change in (
            {"repository": "other/repo"},
            {"owner": "production"},
            {"run_id": "local"},
            {"session": "other"},
            {"purpose": ""},
            {"created_at": "invalid"},
            {"run_attempt": "2"},
        ):
            with self.subTest(change=change):
                item = copy.deepcopy(self.item)
                item["Labels"].update(
                    {module.PREFIX + key: value for key, value in change.items()}
                )
                self.cleaner.consider("container", item)
        item = copy.deepcopy(self.item)
        item["Labels"]["com.docker.compose.project"] = "production"
        self.cleaner.consider("container", item)
        self.assertEqual([], self.mutations())

    def test_active_recent_wrong_workflow_or_wrong_attempt_protected(self):
        for change in (
            {"status": "in_progress"},
            {"status": "queued"},
            {"run_attempt": 2},
            {"path": ".github/workflows/cd-localcluster.yml"},
            {"head_repository": {"full_name": "someone/else"}},
            {"updated_at": self.cleaner.now.isoformat()},
        ):
            with self.subTest(change=change):
                self.api.return_value = dict(self.run, **change)
                self.cleaner.consider("container", self.item)
        self.assertEqual([], self.mutations())

    def test_resource_predating_run_is_not_adopted(self):
        self.run["created_at"] = (self.created + timedelta(hours=1)).isoformat()
        self.cleaner.consider("container", self.item)
        self.assertEqual([], self.mutations())

    def test_naive_future_and_recent_creation_protected(self):
        for value in (
            "2020-01-01T00:00:00",
            self.cleaner.now.isoformat(),
            (self.cleaner.now + timedelta(days=1)).isoformat(),
        ):
            item = dict(self.item, Created=value)
            self.cleaner.consider("container", item)
        self.assertEqual([], self.mutations())

    def test_any_persistent_bind_or_volume_protects_container(self):
        for mount in (
            {"Type": "volume"},
            {"Type": "bind", "RW": False},
            {"Type": "bind", "RW": True},
        ):
            self.cleaner.consider("container", dict(self.item, Mounts=[mount]))
        self.cleaner.consider("container", dict(self.item, Restart="always"))
        self.cleaner.consider("container", dict(self.item, Privileged=True))
        self.assertEqual([], self.mutations())

    def test_api_failure_never_deletes(self):
        for error in (OSError("404"), OSError("429"), OSError("503")):
            self.api.side_effect = error
            with self.assertRaises(OSError):
                self.cleaner.consider("container", self.item)
        self.assertEqual([], self.mutations())

    def test_attempt_becomes_active_before_apply(self):
        self.api.side_effect = [self.run, dict(self.run, status="in_progress")]
        with self.assertRaises(RuntimeError):
            self.cleaner.consider("container", self.item)
        self.assertEqual([], self.mutations())

    def test_changed_identity_aborts(self):
        self.inspection.side_effect = lambda *_: dict(self.item, Id="b" * 64)
        with self.assertRaises(RuntimeError):
            self.cleaner.consider("container", self.item)
        self.assertEqual([], self.mutations())

    def test_changed_mount_after_stop_prevents_removal(self):
        self.item["State"] = "running"
        self.inspection.side_effect = [
            copy.deepcopy(self.item),
            dict(self.item, State="exited", Mounts=[{"Type": "volume"}]),
        ]
        with self.assertRaises(RuntimeError):
            self.cleaner.consider("container", copy.deepcopy(self.item))
        self.assertEqual(["stop"], [args[2] for args in self.mutations()])

    def test_bounded_deletion(self):
        self.cleaner.limit = 1
        self.cleaner.consider("container", self.item)
        self.cleaner.consider("container", self.item)
        self.assertEqual(1, len(self.mutations()))
        self.assertEqual(1, self.cleaner.counts["limited"])

    def network(self):
        return dict(
            {
                key: value
                for key, value in self.item.items()
                if key in ("Id", "Created", "Labels")
            },
            Name="sample-ci-123-1",
            Containers={},
            Driver="bridge",
            Scope="local",
        )

    def test_only_empty_local_bridge_network_removed(self):
        item = self.network()
        self.inspection.side_effect = lambda *_: item
        self.cleaner.consider("network", dict(item, Containers={"consumer": {}}))
        self.cleaner.consider("network", dict(item, Driver="host"))
        self.assertEqual([], self.mutations())
        self.cleaner.consider("network", item)
        self.assertEqual([("docker", "network", "rm", item["Id"])], self.mutations())

    def test_network_name_must_belong_to_the_configured_app(self):
        for name in ("", "production", "other-ci-123-1", "sample-ci-", "sample-ci-Invalid"):
            with self.subTest(name=name):
                self.cleaner.consider("network", dict(self.network(), Name=name))
        item = self.network()
        del item["Name"]
        self.cleaner.consider("network", item)
        self.assertEqual([], self.mutations())

    def test_invalid_app_name_is_rejected(self):
        for name in ("", "Sample", "sample/other", "sample.*"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                module.Cleaner(True, 25, name)

    def test_volumes_are_never_disposable(self):
        volume = {"Name": "sample-ci-123-1-test", "Labels": self.item["Labels"]}
        self.assertFalse(self.cleaner.disposable("volume", volume))


class LockTests(unittest.TestCase):
    @unittest.skipUnless(Path("/proc/self/stat").exists(), "Linux process ancestry")
    def test_matching_local_parent_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "token").write_text("expected")
            with patch.dict(
                os.environ,
                {
                    "LOCALCLUSTER_DEPLOY_LOCK_DIR": directory,
                    "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": "expected",
                },
            ):
                # A token alone is insufficient, even with the correct hostname.
                (root / "owner").write_text(
                    f"{module.socket.gethostname()}:pid={os.getpid()}:started=test"
                )
                with self.assertRaises(RuntimeError):
                    module.require_lock()
                (root / "owner").write_text(
                    f"{module.socket.gethostname()}:pid={os.getppid()}:started=test"
                )
                module.require_lock()

    def test_apply_requires_real_lock_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                module.require_lock()

    def test_foreign_owner_or_wrong_token_cannot_bypass_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "token").write_text("expected")
            (root / "owner").write_text("foreign:pid=1:started=old")
            for token in ("wrong", "expected"):
                with patch.dict(
                    os.environ,
                    {
                        "LOCALCLUSTER_DEPLOY_LOCK_DIR": directory,
                        "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": token,
                    },
                ):
                    with self.assertRaises(RuntimeError):
                        module.require_lock()


if __name__ == "__main__":
    unittest.main()
