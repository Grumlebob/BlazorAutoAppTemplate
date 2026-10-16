from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "ci_report_store.py"
SPEC = importlib.util.spec_from_file_location("ci_report_store", SCRIPT)
assert SPEC and SPEC.loader
store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(store)


class CiReportStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ci-report-store-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "store"
        self.source = Path(self.temporary.name) / "source"
        self.source.mkdir()
        self.now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
        self.trx = self.source / "suite.trx"
        self.trx.write_text(
            """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
  <ResultSummary outcome="Failed"><Counters total="5" executed="5" passed="4" failed="1" error="1" notExecuted="2" /></ResultSummary>
</TestRun>
""",
            encoding="utf-8",
        )

    def save(self, *, run_id: str = "123", attempt: str = "1", job: str = "validate", status: str = "failure", max_bytes: int = store.DEFAULT_MAX_BYTES, source: Path | None = None, now: datetime | None = None):
        return store.save_report(
            source=source or self.source,
            root=self.root,
            run_id=run_id,
            attempt=attempt,
            job=job,
            status=status,
            max_bytes=max_bytes,
            now=now or self.now,
        )

    def test_saves_trx_counts_retrieves_payload_and_lists_identity(self) -> None:
        summary_path = Path(self.temporary.name) / "summary.md"
        metadata = store.save_report(
            source=self.source,
            root=self.root,
            run_id="123",
            attempt="2",
            job="validate",
            status="failure",
            step_summary=summary_path,
            runner_name="improveddb-ci-desktop",
            now=self.now,
        )

        self.assertEqual(metadata["trx_counts"]["total"], 5)
        self.assertEqual(metadata["trx_counts"]["passed"], 4)
        self.assertEqual(metadata["trx_counts"]["failed"], 1)
        self.assertEqual(metadata["trx_counts"]["notExecuted"], 2)
        self.assertEqual(metadata["trx_count"], 1)
        self.assertEqual(metadata["repository"], store.DEFAULT_REPOSITORY)
        self.assertEqual(store.list_reports(self.root)[0]["job"], "validate")
        self.assertIn("improveddb-ci-desktop", summary_path.read_text(encoding="utf-8"))
        self.assertIn("--run-id 123 --attempt 2 --job validate", summary_path.read_text(encoding="utf-8"))

        destination = Path(self.temporary.name) / "restored"
        store.restore_report(self.root, "123", "2", "validate", destination)
        self.assertEqual((destination / "suite.trx").read_bytes(), self.trx.read_bytes())

        with self.assertRaisesRegex(store.ReportStoreError, "outside the report store"):
            store.restore_report(self.root, "123", "2", "validate", self.root / "nested-report")

    def test_retention_expires_success_after_three_days_and_failure_after_seven(self) -> None:
        success_time = self.now - timedelta(days=3)
        failure_time = self.now - timedelta(days=7)
        for run_id, status, timestamp in (
            ("101", "success", success_time),
            ("102", "failure", failure_time),
            ("103", "failure", failure_time + timedelta(minutes=1)),
        ):
            store.save_report(
                source=self.source,
                root=self.root,
                run_id=run_id,
                attempt="1",
                job="validate",
                status=status,
                now=timestamp,
            )

        removed = store._prune(self.root, now=self.now, max_bytes=store.DEFAULT_MAX_BYTES)
        self.assertEqual(set(removed), {"101-1-validate", "102-1-validate"})
        self.assertEqual({manifest["run_id"] for _, manifest in store._known_entries(self.root)}, {"103"})

    def test_pinned_and_unknown_entries_are_preserved_when_byte_cap_is_reached(self) -> None:
        first = self.save(run_id="101", status="success")
        store._mutate_pin(self.root, "101", "1", "validate", True)
        unknown = self.root / "unknown-owner-data"
        unknown.mkdir()
        (unknown / "data.bin").write_bytes(b"unknown")

        with self.assertRaisesRegex(store.ReportStoreError, "byte cap"):
            self.save(run_id="102", status="failure", max_bytes=1)

        self.assertTrue((self.root / "101-1-validate").exists())
        self.assertTrue((self.root / "unknown-owner-data" / "data.bin").exists())
        self.assertFalse((self.root / "102-1-validate").exists())
        self.assertTrue(first["report_bytes"] > 0)

    def test_cap_prunes_oldest_unpinned_reports(self) -> None:
        self.save(run_id="101", status="success", now=self.now - timedelta(minutes=2))
        self.save(run_id="102", status="success", now=self.now - timedelta(minutes=1))
        newest = self.save(run_id="103", status="success")

        removed = store._prune(
            self.root,
            now=self.now,
            max_bytes=store._safe_tree_bytes(self.root / "103-1-validate") + 64,
        )
        self.assertIn("101-1-validate", removed)
        self.assertIn("102-1-validate", removed)
        self.assertEqual(store._known_entries(self.root)[0][1]["run_id"], "103")
        self.assertGreater(newest["report_bytes"], 0)

    def test_rejects_duplicate_identity_and_symlink_inputs(self) -> None:
        self.save()
        with self.assertRaisesRegex(store.ReportStoreError, "already exists"):
            self.save()

        link_source = Path(self.temporary.name) / "link-source"
        link_source.mkdir()
        (link_source / "external.trx").symlink_to(self.trx)
        with self.assertRaisesRegex(store.ReportStoreError, "symbolic links"):
            self.save(run_id="124", source=link_source)

    def test_skips_cancelled_reports_and_pin_changes_require_a_known_entry(self) -> None:
        result = store.save_report(
            source=self.source,
            root=self.root,
            run_id="125",
            attempt="1",
            job="validate",
            status="cancelled",
            now=self.now,
        )
        self.assertIsNone(result)
        self.assertEqual(store.list_reports(self.root), [])
        with self.assertRaisesRegex(store.ReportStoreError, "no valid report"):
            store._mutate_pin(self.root, "125", "1", "validate", True)

    def test_report_identity_and_default_root_are_scoped_by_repository(self) -> None:
        other_repository = "example/another-template"
        store.save_report(
            source=self.source,
            root=self.root,
            run_id="126",
            attempt="1",
            job="validate",
            status="failure",
            repository=other_repository,
            now=self.now,
        )

        self.assertEqual([report["repository"] for report in store.list_reports(self.root)], [])
        other_reports = store.list_reports(self.root, other_repository)
        self.assertEqual([report["run_id"] for report in other_reports], ["126"])
        self.assertNotEqual(store.default_root(store.DEFAULT_REPOSITORY), store.default_root(other_repository))
        self.assertEqual(
            store.default_root(other_repository),
            Path.home() / ".local" / "state" / "github-actions-reports" / "example" / "another-template",
        )

    def test_report_root_override_still_keeps_repositories_separate(self) -> None:
        base = Path(self.temporary.name) / "report-base"
        with patch.dict("os.environ", {"CI_REPORT_ROOT": str(base)}):
            template_root = store.default_root(store.DEFAULT_REPOSITORY)
            portfolio_root = store.default_root("Grumlebob/Portfolio")
        self.assertEqual(template_root, base / "grumlebob" / "blazorautoapptemplate")
        self.assertEqual(portfolio_root, base / "grumlebob" / "portfolio")

    def test_prune_cli_removes_only_expired_reports_for_selected_repository(self) -> None:
        old_time = self.now - timedelta(days=4)
        for repository, run_id in ((store.DEFAULT_REPOSITORY, "127"), ("example/other", "128")):
            store.save_report(
                source=self.source,
                root=self.root,
                run_id=run_id,
                attempt="1",
                job="validate",
                status="success",
                repository=repository,
                now=old_time,
            )

        output = io.StringIO()
        with patch.object(store, "datetime") as date_mock:
            date_mock.now.return_value = self.now
            date_mock.fromisoformat = datetime.fromisoformat
            with redirect_stdout(output):
                status = store.main([
                    "prune", "--repository", store.DEFAULT_REPOSITORY,
                    "--root", str(self.root),
                ])

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["removed"], ["127-1-validate"])
        self.assertFalse((self.root / "127-1-validate").exists())
        self.assertTrue((self.root / "128-1-validate").exists())

    def test_prune_dry_run_and_unknown_entries_fail_closed(self) -> None:
        self.save(run_id="129", status="success", now=self.now - timedelta(days=4))
        output = io.StringIO()
        with patch.object(store, "datetime") as date_mock:
            date_mock.now.return_value = self.now
            date_mock.fromisoformat = datetime.fromisoformat
            with redirect_stdout(output):
                self.assertEqual(store.main([
                    "prune", "--repository", store.DEFAULT_REPOSITORY,
                    "--root", str(self.root), "--dry-run",
                ]), 0)

        preview = json.loads(output.getvalue())
        self.assertEqual(preview["planned"], ["129-1-validate"])
        self.assertEqual(preview["removed"], [])
        self.assertTrue(preview["dry_run"])
        self.assertTrue((self.root / "129-1-validate").exists())

        unknown = self.root / "unknown-owner-data"
        unknown.mkdir()
        (unknown / "data.bin").write_bytes(b"unknown")
        output = io.StringIO()
        with patch.object(store, "datetime") as date_mock:
            date_mock.now.return_value = self.now
            date_mock.fromisoformat = datetime.fromisoformat
            with redirect_stdout(output):
                self.assertEqual(store.main([
                    "prune", "--repository", store.DEFAULT_REPOSITORY,
                    "--root", str(self.root),
                ]), 0)

        blocked = json.loads(output.getvalue())
        self.assertEqual(blocked["blocked_reason"], "unknown_store_entries")
        self.assertEqual(blocked["planned"], [])
        self.assertEqual(blocked["removed"], [])
        self.assertEqual(blocked["unknown_entries"], ["unknown-owner-data"])
        self.assertTrue((self.root / "129-1-validate").exists())
        self.assertTrue(unknown.exists())


if __name__ == "__main__":
    unittest.main()
