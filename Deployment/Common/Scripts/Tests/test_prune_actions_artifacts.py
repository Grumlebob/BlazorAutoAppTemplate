#!/usr/bin/env python3
"""Retention selection for prune-actions-artifacts.py; no GitHub calls."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "Component/lib/prune-actions-artifacts.py"
SPEC = importlib.util.spec_from_file_location("prune_actions_artifacts", SCRIPT)
assert SPEC and SPEC.loader
prune = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prune)


def artifact(artifact_id: int, run_id: int | None, day: int) -> dict:
    item = {"id": artifact_id, "created_at": f"2026-10-{day:02d}T00:00:00Z"}
    if run_id is not None:
        item["workflow_run"] = {"id": run_id}
    return item


class SelectDeletionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifacts = [artifact(index, 1000 + index, index) for index in range(1, 7)]

    def ids(self, items: list[dict]) -> list[int]:
        return [item["id"] for item in items]

    def test_keeps_newest_and_deletes_the_rest(self) -> None:
        delete, protected = prune.select_deletions(self.artifacts, 2, set())
        self.assertEqual([4, 3, 2, 1], self.ids(delete))
        self.assertEqual([], protected)

    def test_protected_runs_are_never_deleted(self) -> None:
        delete, protected = prune.select_deletions(self.artifacts, 2, {1001, 1003})
        self.assertEqual([4, 2], self.ids(delete))
        self.assertEqual([3, 1], self.ids(protected))

    def test_unidentified_run_is_kept_when_any_run_is_protected(self) -> None:
        artifacts = self.artifacts + [artifact(99, None, 0)]
        delete, protected = prune.select_deletions(artifacts, 2, {1001})
        self.assertNotIn(99, self.ids(delete))
        self.assertIn(99, self.ids(protected))

    def test_keep_floor_applies_before_protection(self) -> None:
        delete, protected = prune.select_deletions(self.artifacts, 10, {1001})
        self.assertEqual([], delete)
        self.assertEqual([], protected)


if __name__ == "__main__":
    unittest.main()
