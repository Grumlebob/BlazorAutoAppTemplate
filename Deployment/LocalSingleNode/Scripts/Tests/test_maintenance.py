from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
from unittest import TestCase

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import maintenance  # noqa: E402

SOURCE = "https://github.com/Grumlebob/BlazorAutoAppTemplate"
APP = "ghcr.io/grumlebob/books"
PAYLOAD = "ghcr.io/grumlebob/books-release-payload"
NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
OLD = "2026-10-15T12:00:00Z"
RELEASE = {"image": APP, "digest": "sha256:" + "f" * 64, "source_repo_url": SOURCE}


def image_id(number):
    return f"sha256:{number:064x}"


def image_in(repository, number):
    digest = image_id(number)
    return {"Id": digest, "Created": OLD, "RepoTags": [f"{repository}:run-{number}"],
            "RepoDigests": [f"{repository}@{digest}"],
            "Config": {"Labels": {"org.opencontainers.image.source": SOURCE}}}


def inspect_answers(images):
    return {("image", "inspect", image["Id"]): (True, json.dumps([image])) for image in images}


class FakeDocker:
    """Answers docker calls from a table (success with no output by default) and records every call."""

    def __init__(self, answers=()):
        self.answers = dict(answers)
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return self.answers.get(args, (True, ""))

    def removed(self):
        return [call[2] for call in self.calls if call[:2] == ("image", "rm")]


class PayloadRemovalTests(TestCase):
    def setUp(self):
        self.first = image_in(PAYLOAD, 1)
        self.second = image_in(PAYLOAD, 2)
        self.images = [self.first, self.second]
        self.answers = inspect_answers(self.images)

    def remove(self, docker):
        with redirect_stdout(io.StringIO()):
            return maintenance.remove_payload_images(self.images, [], RELEASE, NOW, (), docker, lambda: ())

    def test_refused_untag_is_reported_and_the_next_image_is_still_removed(self):
        tag = f"{PAYLOAD}:run-1"
        docker = FakeDocker({**self.answers, ("image", "rm", tag): (False, "conflict: image is in use")})
        refused = self.remove(docker)
        self.assertEqual(len(refused), 1)
        self.assertIn(self.first["Id"], refused[0])
        self.assertIn("conflict: image is in use", refused[0])
        self.assertIn(f"{PAYLOAD}:run-2", docker.removed())
        self.assertNotIn(self.first["Id"], docker.removed())

    def test_successful_removal_untags_before_removing_the_id_and_never_forces(self):
        docker = FakeDocker(self.answers)
        self.assertEqual(self.remove(docker), [])
        self.assertEqual(docker.removed(), [f"{PAYLOAD}:run-1", self.first["Id"], f"{PAYLOAD}:run-2", self.second["Id"]])
        self.assertTrue(all(arg not in ("-f", "--force") for call in docker.calls for arg in call))

    def test_image_gone_since_the_snapshot_is_skipped(self):
        docker = FakeDocker({**self.answers, ("image", "inspect", self.first["Id"]): (False, "No such image")})
        self.assertEqual(self.remove(docker), [])
        self.assertEqual(docker.removed(), [f"{PAYLOAD}:run-2", self.second["Id"]])

    def test_container_reference_leaves_the_image_in_place(self):
        docker = FakeDocker({**self.answers, ("ps", "-aq", "--filter", "ancestor=" + self.first["Id"]): (True, "abc123")})
        self.assertEqual(self.remove(docker), [])
        self.assertNotIn(f"{PAYLOAD}:run-1", docker.removed())
        self.assertNotIn(self.first["Id"], docker.removed())

    def test_failed_container_check_is_refused_rather_than_assumed_safe(self):
        docker = FakeDocker({**self.answers, ("ps", "-aq", "--filter", "ancestor=" + self.first["Id"]): (False, "daemon unavailable")})
        refused = self.remove(docker)
        self.assertEqual(len(refused), 1)
        self.assertIn("container check failed", refused[0])
        self.assertNotIn(f"{PAYLOAD}:run-1", docker.removed())


class AppRemovalTests(TestCase):
    def test_refused_removal_does_not_stop_the_next_image(self):
        first, second = image_in(APP, 3), image_in(APP, 4)
        images = [first, second]
        docker = FakeDocker({**inspect_answers(images), ("image", "rm", first["Id"]): (False, "conflict: must be forced")})
        with redirect_stdout(io.StringIO()):
            refused = maintenance.remove_app_images(images, [], RELEASE, NOW, (), docker, lambda: ())
        self.assertEqual(len(refused), 1)
        self.assertIn("conflict: must be forced", refused[0])
        self.assertIn(second["Id"], docker.removed())
