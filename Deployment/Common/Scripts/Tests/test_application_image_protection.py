"""Protect accepted/recovery bytes and active consumers before image cleanup."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Component/lib"))
import release_status
from release_status import ReleaseStatusError, protected_application_image_references, verify_cached_application_image


class ApplicationImageProtectionTests(unittest.TestCase):
    def test_maintenance_passes_protected_identity_to_status_reader(self):
        root = Path(__file__).resolve().parents[4]
        step = (root / '.github/workflows/localsinglenode-maintenance.yml').read_text().split('- name: Protected backup and scoped maintenance', 1)[1].split('- name:', 1)[0]
        self.assertIn('LOCALSINGLENODE_HOST: ${{ vars.LOCALSINGLENODE_HOST }}', step)
        self.assertIn('GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}', step)

    image = "ghcr.io/fixture-owner/app"

    def status(self):
        return dict(schema_version=1, repository="fixture-owner/repository", shared_lock="held",
                    mutation="none", live_identity="verified", current_pin="verified", recovery_pin="verified",
                    current_release=dict(image=self.image, digest="sha256:" + "a" * 64, source_sha="1" * 40),
                    recovery_release=dict(image=self.image, digest="sha256:" + "b" * 64, source_sha="2" * 40),
                    active_deployments=[dict(target_sha="3" * 40)])

    def references(self, value):
        return protected_application_image_references(value, repository="fixture-owner/repository", app_image=self.image)

    def test_previous_release_and_active_target_are_protected_with_current(self):
        references = self.references(self.status())
        self.assertIn(self.image + "@sha256:" + "a" * 64, references)
        self.assertIn(self.image + "@sha256:" + "b" * 64, references)
        self.assertIn(self.image + ":" + "3" * 40, references)
        self.assertEqual(len(references), 5)

    def test_missing_or_unverified_recovery_cannot_authorize_deletion(self):
        for change in ({"recovery_release": None}, {"recovery_pin": "missing"}, {"active_deployments": None}):
            with self.subTest(change=change), self.assertRaises(ReleaseStatusError):
                self.references({**self.status(), **change})

    def test_foreign_unlocked_mutating_or_unverified_status_cannot_authorize_deletion(self):
        for change in ({"repository": "other/repository"}, {"shared_lock": "absent"},
                       {"mutation": "deploy"}, {"live_identity": "failed"}):
            with self.subTest(change=change), self.assertRaises(ReleaseStatusError):
                self.references({**self.status(), **change})

    def test_corrupt_digest_foreign_image_and_unknown_active_target_fail_closed(self):
        for slot, field, value in (("recovery_release", "digest", "bad"),
                                   ("current_release", "image", "ghcr.io/other/app"),
                                   ("current_release", "source_sha", "unknown")):
            status = deepcopy(self.status())
            status[slot][field] = value
            with self.subTest(field=field), self.assertRaises(ReleaseStatusError):
                self.references(status)
        status = self.status()
        status["active_deployments"] = [dict(target_sha=None)]
        with self.assertRaises(ReleaseStatusError):
            self.references(status)

    def test_offline_inspection_uses_only_the_exact_local_digest(self):
        release = self.status()["recovery_release"]
        reference = self.image + "@" + release["digest"]
        row = {"Id": "sha256:" + "c" * 64, "RepoDigests": [reference]}
        with patch.object(release_status.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps([row]))) as run:
            verify_cached_application_image(release)
        run.assert_called_once_with(["docker", "image", "inspect", reference], capture_output=True, text=True, check=True, timeout=30)

    def test_missing_or_different_cached_image_fails_without_a_pull(self):
        release = self.status()["recovery_release"]
        for result in ([], [{"Id": "sha256:" + "c" * 64, "RepoDigests": [self.image + "@sha256:" + "d" * 64]}]):
            with self.subTest(result=result), patch.object(release_status.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(result))) as run:
                with self.assertRaisesRegex(ReleaseStatusError, "no pull was attempted"):
                    verify_cached_application_image(release)
                self.assertEqual(run.call_count, 1)
        with patch.object(release_status.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "docker")) as run:
            with self.assertRaisesRegex(ReleaseStatusError, "no pull was attempted"):
                verify_cached_application_image(release)
            self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
