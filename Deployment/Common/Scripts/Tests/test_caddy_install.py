"""Offline migration fixtures: preserve foreign apt sources and existing backups."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "retire-caddy-cloudsmith-source.py"
SPEC = importlib.util.spec_from_file_location("caddy_source", SCRIPT)
caddy_source = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(caddy_source)


class LegacyCaddySourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "caddy-stable.list"
        self.content = "# Source: Caddy\n\n" + "\n".join(
            f"{kind} {caddy_source.OPTIONS} {caddy_source.REPOSITORY} any-version main"
            for kind in ("deb", "deb-src")
        ) + "\n"

    def test_exact_legacy_source_is_preserved_and_rerun_is_unchanged(self):
        self.source.write_text(self.content)
        self.assertTrue(caddy_source.retire(self.source))
        self.assertFalse(self.source.exists())
        self.assertEqual(self.content, self.source.with_suffix(".list.disabled").read_text())
        self.assertFalse(caddy_source.retire(self.source))

    def test_foreign_or_mixed_source_is_untouched(self):
        for content in ("", "# operator source\n", self.content.replace("any-version", "custom"), self.content + "deb https://example.invalid stable main\n"):
            with self.subTest(content=content):
                self.source.write_text(content)
                with self.assertRaisesRegex(ValueError, "Foreign"):
                    caddy_source.retire(self.source)
                self.assertEqual(content, self.source.read_text())
                self.assertFalse(self.source.with_suffix(".list.disabled").exists())

    def test_symlink_source_or_backup_is_untouched(self):
        target = self.source.parent / "operator.list"
        target.write_text(self.content)
        self.source.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            caddy_source.retire(self.source)
        self.source.unlink()
        self.source.write_text(self.content)
        self.source.with_suffix(".list.disabled").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            caddy_source.retire(self.source)
        self.assertEqual(self.content, target.read_text())
        self.assertEqual(self.content, self.source.read_text())

    def test_existing_foreign_backup_is_not_overwritten(self):
        self.source.write_text(self.content)
        backup = self.source.with_suffix(".list.disabled")
        backup.write_text("operator backup\n")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            caddy_source.retire(self.source)
        self.assertEqual("operator backup\n", backup.read_text())
        self.assertEqual(self.content, self.source.read_text())

    def test_reintroduced_identical_source_reuses_backup(self):
        self.source.write_text(self.content)
        backup = self.source.with_suffix(".list.disabled")
        backup.write_text(self.content)
        self.assertTrue(caddy_source.retire(self.source))
        self.assertEqual(self.content, backup.read_text())
        self.assertFalse(self.source.exists())


if __name__ == "__main__":
    unittest.main()
