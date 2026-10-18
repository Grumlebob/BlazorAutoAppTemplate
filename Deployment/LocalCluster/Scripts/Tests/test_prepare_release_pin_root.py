from pathlib import Path
import os
import stat
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "prepare-release-pin-root.sh"


class PrepareReleasePinRootTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        tools = self.base / "bin"
        tools.mkdir()
        sudo = tools / "sudo"
        sudo.write_text('#!/bin/sh\n[ "$1" = -n ] || exit 80\nshift\nexec "$@"\n')
        sudo.chmod(0o755)
        self.env = {**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]}

    def run_script(self, root):
        return subprocess.run(["bash", str(SCRIPT), str(root)], env=self.env,
                              capture_output=True, text=True)

    def test_missing_root_becomes_private_owned_directory_before_pinning(self):
        root = self.base / "app"
        result = self.run_script(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(root.stat().st_uid, os.getuid())
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o750)
        (root / "release-payloads").mkdir()

    def test_existing_root_and_payload_bytes_are_preserved(self):
        root = self.base / "app"
        root.mkdir(mode=0o700)
        payload = root / "existing-pin"
        payload.write_bytes(b"verified release bytes")
        result = self.run_script(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
        self.assertEqual(payload.read_bytes(), b"verified release bytes")

    def test_symlinked_root_or_parent_cannot_redirect_privileged_creation(self):
        outside = self.base / "outside"
        outside.mkdir(mode=0o700)
        link = self.base / "link"
        link.symlink_to(outside, target_is_directory=True)
        for root in (link, link / "app"):
            with self.subTest(root=root):
                self.assertNotEqual(self.run_script(root).returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(stat.S_IMODE(outside.stat().st_mode), 0o700)

    def test_file_relative_and_parent_traversal_paths_fail_without_mutation(self):
        existing = self.base / "file"
        existing.write_bytes(b"preserve")
        for root in (existing, "relative", self.base / "app/../other", "/"):
            with self.subTest(root=root):
                self.assertNotEqual(self.run_script(root).returncode, 0)
        self.assertEqual(existing.read_bytes(), b"preserve")
        self.assertFalse((self.base / "other").exists())


if __name__ == "__main__":
    unittest.main()
