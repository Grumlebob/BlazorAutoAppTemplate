from pathlib import Path
import re
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[4]
PUBLIC_E2E = ROOT / "Scripts/Testing/RunReactPublicE2E.ps1"


class CiVolumeHygieneTests(TestCase):
    """CI test containers on the shared runner must not leave anonymous Docker volumes behind.

    postgres:18 declares /var/lib/postgresql and redis declares /data as volumes. A forced removal keeps
    anonymous volumes, which once left about one 50 MB PostgreSQL volume per CI run on the node.
    """

    def run_arguments(self, image_variable):
        source = PUBLIC_E2E.read_text(encoding="utf-8")
        for block in re.findall(r"Invoke-CheckedCommand -FilePath 'docker' -Arguments @\((.*?)\n\s*\)", source, re.S):
            if "'run'" in block and block.rstrip().endswith(image_variable):
                return block
        self.fail(f"no docker run for {image_variable} in {PUBLIC_E2E.name}")

    def test_public_e2e_postgres_keeps_its_data_on_tmpfs(self):
        self.assertIn("'--tmpfs', '/var/lib/postgresql:rw,size=1073741824'", self.run_arguments("$postgresImage"))

    def test_public_e2e_redis_keeps_its_data_on_tmpfs(self):
        self.assertIn("'--tmpfs', '/data:rw,size=67108864'", self.run_arguments("$redisImage"))

    def test_public_e2e_cleanup_removes_anonymous_volumes(self):
        source = PUBLIC_E2E.read_text(encoding="utf-8")
        removals = re.findall(r"docker rm [^\n]*", source)
        self.assertTrue(removals)
        for removal in removals:
            self.assertIn("--volumes", removal)
