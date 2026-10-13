#!/usr/bin/env python3
"""Test bounded deployment-document loading without running the full audit."""

import sys
import tempfile
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "Component" / "lib"
sys.path.insert(0, str(LIB))

from doc_slice_loader import (  # noqa: E402
    CLUSTER_ENTRY,
    DocumentSliceError,
    fence_error,
    load_document_slices,
    missing_literal,
    missing_section_literal,
    missing_target_scripts,
)


class DocumentSliceLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.entry_text = "# LocalCluster guide\n"
        self._write(CLUSTER_ENTRY, self.entry_text)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, relative_path, text):
        path = self.repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_baseline_entry_loads_with_empty_slice_declaration(self):
        documents = load_document_slices(
            self.repo_root,
            CLUSTER_ENTRY,
            {CLUSTER_ENTRY: ()},
        )

        self.assertEqual({CLUSTER_ENTRY: self.entry_text}, documents)

    def test_linked_split_loads_direct_and_intermediate_slices(self):
        self.entry_text = "# LocalCluster guide\n[Setup](Setup.md#first-host)\n"
        self._write(CLUSTER_ENTRY, self.entry_text)
        setup = "# Setup\n[SSH trust](../Common/SshTrust.md#verified-host-keys)\n"
        trust = "# SSH trust\nAppend the same scanned key only after the fingerprints match\n"
        self._write("Deployment/LocalCluster/Setup.md", setup)
        self._write("Deployment/Common/SshTrust.md", trust)

        documents = load_document_slices(
            self.repo_root,
            CLUSTER_ENTRY,
            {
                CLUSTER_ENTRY: (
                    "Deployment/LocalCluster/Setup.md",
                    "Deployment/Common/SshTrust.md",
                )
            },
        )

        self.assertEqual(3, len(documents))
        self.assertIsNone(
            missing_literal(
                documents,
                CLUSTER_ENTRY,
                "Deployment/Common/SshTrust.md",
                "Append the same scanned key only after the fingerprints match",
                "verified SSH host key acceptance",
            )
        )

    def test_declared_missing_slice_fails_with_its_path(self):
        with self.assertRaisesRegex(DocumentSliceError, "Setup.md: declared documentation slice does not exist"):
            load_document_slices(
                self.repo_root,
                CLUSTER_ENTRY,
                {CLUSTER_ENTRY: ("Deployment/LocalCluster/Setup.md",)},
            )

    def test_unreachable_safety_slice_fails(self):
        self._write("Deployment/LocalCluster/Setup.md", "# Setup\n")

        with self.assertRaisesRegex(DocumentSliceError, "declared documentation slice is unreachable"):
            load_document_slices(
                self.repo_root,
                CLUSTER_ENTRY,
                {CLUSTER_ENTRY: ("Deployment/LocalCluster/Setup.md",)},
            )

    def test_links_inside_code_fences_do_not_make_a_slice_reachable(self):
        self.entry_text = "```md\n    ```\n[Setup](Setup.md)\n```\n"
        self._write(CLUSTER_ENTRY, self.entry_text)
        self._write("Deployment/LocalCluster/Setup.md", "# Setup\n")

        with self.assertRaisesRegex(DocumentSliceError, "declared documentation slice is unreachable"):
            load_document_slices(
                self.repo_root,
                CLUSTER_ENTRY,
                {CLUSTER_ENTRY: ("Deployment/LocalCluster/Setup.md",)},
            )

    def test_links_inside_inline_code_do_not_make_a_slice_reachable(self):
        self.entry_text = "`[Setup](Setup.md)`\n"
        self._write(CLUSTER_ENTRY, self.entry_text)
        self._write("Deployment/LocalCluster/Setup.md", "# Setup\n")

        with self.assertRaisesRegex(DocumentSliceError, "declared documentation slice is unreachable"):
            load_document_slices(
                self.repo_root,
                CLUSTER_ENTRY,
                {CLUSTER_ENTRY: ("Deployment/LocalCluster/Setup.md",)},
            )

    def test_slice_outside_allowed_document_roots_fails(self):
        self._write("Plans.local/Contract.md", "# Private plan notes\n")

        with self.assertRaisesRegex(DocumentSliceError, "outside the allowed documentation roots"):
            load_document_slices(
                self.repo_root,
                CLUSTER_ENTRY,
                {CLUSTER_ENTRY: ("Plans.local/Contract.md",)},
            )

    def test_absent_declaration_does_not_load_undeclared_linked_guidance(self):
        self.entry_text = "# Guide\n[Required setup](Setup.md)\n"
        self._write(CLUSTER_ENTRY, self.entry_text)
        self._write("Deployment/LocalCluster/Setup.md", "required safety rule\n")
        documents = load_document_slices(self.repo_root, CLUSTER_ENTRY, {CLUSTER_ENTRY: ()})

        self.assertNotIn("Deployment/LocalCluster/Setup.md", documents)
        self.assertIn(
            f"{CLUSTER_ENTRY}: missing required setup rule",
            missing_literal(
                documents,
                CLUSTER_ENTRY,
                "Deployment/LocalCluster/Setup.md",
                "required safety rule",
                "required setup rule",
            ),
        )

    def test_missing_required_rule_fails_in_the_fallback_entry(self):
        documents = load_document_slices(self.repo_root, CLUSTER_ENTRY, {CLUSTER_ENTRY: ()})

        self.assertIn(
            f"{CLUSTER_ENTRY}: missing deployment lock recovery guidance",
            missing_literal(
                documents,
                CLUSTER_ENTRY,
                "Deployment/LocalCluster/Operations.md",
                "### Deployment lock",
                "deployment lock recovery guidance",
            ),
        )

    def test_missing_identity_from_non_reuse_list_fails(self):
        settings_path = "Deployment/LocalCluster/Settings.md"
        self.entry_text = "# Guide\n[Settings](Settings.md)\n"
        self._write(CLUSTER_ENTRY, self.entry_text)
        self._write(
            settings_path,
            "For a second fork on the same nodes, do not reuse these values from the first app\n"
            "- `app_image`\n\n"
            "The second fork normally reuses the same machine IPs\n",
        )
        documents = load_document_slices(
            self.repo_root,
            CLUSTER_ENTRY,
            {CLUSTER_ENTRY: (settings_path,)},
        )

        self.assertEqual(
            f"{settings_path}: missing side-by-side app identity field listed for non-reuse: `app_name`",
            missing_section_literal(
                documents,
                CLUSTER_ENTRY,
                settings_path,
                "For a second fork on the same nodes, do not reuse these values from the first app",
                "The second fork normally reuses the same machine IPs",
                "`app_name`",
                "side-by-side app identity field listed for non-reuse",
            ),
        )

    def test_missing_settings_key_fails_in_the_declared_settings_owner(self):
        settings_path = "Deployment/LocalCluster/Settings.md"
        self.entry_text = "# Guide\n[Settings](Settings.md)\n"
        self._write(CLUSTER_ENTRY, self.entry_text)
        self._write(settings_path, "# Settings\n`app_name`\n")
        documents = load_document_slices(
            self.repo_root,
            CLUSTER_ENTRY,
            {CLUSTER_ENTRY: (settings_path,)},
        )

        self.assertIn(
            f"{settings_path}: missing all.yml setting documentation: `app_port`",
            missing_literal(
                documents,
                CLUSTER_ENTRY,
                settings_path,
                "`app_port`",
                "all.yml setting documentation",
            ),
        )

    def test_unbalanced_fence_error_names_the_file(self):
        self.assertEqual(
            "Deployment/LocalCluster/Setup.md: unbalanced markdown code fences",
            fence_error("Deployment/LocalCluster/Setup.md", "```bash\necho ready\n"),
        )
        self.assertIsNone(fence_error("Deployment/LocalCluster/Setup.md", "```bash\necho ready\n```\n"))

    def test_missing_referenced_target_script_names_guide_and_script(self):
        errors = missing_target_scripts(
            self.repo_root,
            "Deployment/LocalCluster/Setup.md",
            "Run `Deployment/LocalCluster/Scripts/missing-check.sh`.\n",
        )

        self.assertEqual(
            [
                "Deployment/LocalCluster/Setup.md: references missing script: "
                "Deployment/LocalCluster/Scripts/missing-check.sh"
            ],
            errors,
        )

    def test_entry_without_declaration_fails(self):
        with self.assertRaisesRegex(DocumentSliceError, "no documentation-slice declaration exists"):
            load_document_slices(self.repo_root, CLUSTER_ENTRY, {})


if __name__ == "__main__":
    unittest.main()
