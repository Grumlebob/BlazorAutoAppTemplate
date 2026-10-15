from __future__ import annotations

import sys
import unittest
from pathlib import Path


LIB = Path(__file__).resolve().parents[1] / "Component" / "lib"
sys.path.insert(0, str(LIB))
from release_settings import (  # noqa: E402
    apply_defaults,
    derive_release_payload_image,
    validate,
    validate_profile_name,
    validate_release_payload_image,
)


class ReleaseSettingsTests(unittest.TestCase):
    def test_derives_payload_package_and_keeps_existing_release_names(self) -> None:
        values = {
            "app_image": "ghcr.io/grumlebob/books",
            "migration_bundle_name": "books-migrate",
            "migration_runtime": "linux-x64",
        }

        self.assertEqual(validate(values), [])
        resolved = apply_defaults(values)
        self.assertEqual(resolved["release_payload_image"], "ghcr.io/grumlebob/books-release-payload")
        self.assertEqual(resolved["migration_artifact_name"], "books-migrate-linux-x64")
        self.assertEqual(derive_release_payload_image("ghcr.io/grumlebob/books-react"),
                         "ghcr.io/grumlebob/books-react-release-payload")
        self.assertEqual(derive_release_payload_image("ghcr.io/grumlebob/books", "private-"),
                         "ghcr.io/grumlebob/private-books-release-payload")
        self.assertEqual(validate_release_payload_image(
            "ghcr.io/grumlebob/books", "ghcr.io/grumlebob/private-books-release-payload"
        ), "ghcr.io/grumlebob/private-books-release-payload")

    def test_configured_prefix_derives_private_replacement_without_overriding_image(self) -> None:
        values = {
            "app_image": "ghcr.io/grumlebob/books",
            "migration_bundle_name": "books-migrate",
            "migration_runtime": "linux-x64",
            "release_payload_prefix": "private-",
        }
        self.assertEqual(validate(values), [])
        resolved = apply_defaults(values)
        self.assertEqual(resolved["release_payload_image"], "ghcr.io/grumlebob/private-books-release-payload")
        self.assertEqual(resolved["release_payload_prefix"], "private-")

    def test_rejects_unsafe_or_tagged_image_paths(self) -> None:
        for image in (
            "ghcr.io/Grumlebob/books",
            "ghcr.io/grumlebob/books:latest",
            "ghcr.io/grumlebob/books@sha256:" + "a" * 64,
            "ghcr.io/grumlebob/../private",
            "ghcr.io/grumlebob//books",
            "ghcr.io/grumlebob/books/",
        ):
            with self.subTest(image=image):
                self.assertTrue(any("app_image" in error for error in validate({
                    "app_image": image,
                    "migration_bundle_name": "books-migrate",
                    "migration_runtime": "linux-x64",
                })))

    def test_rejects_unsafe_profile_names(self) -> None:
        for profile in ("", "../React", "React:latest", "React/Blazor", "React\nother=value", "a" * 33):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                validate_profile_name(profile)
        self.assertEqual(validate_profile_name("BlazorAuto"), "BlazorAuto")
        self.assertEqual(validate_profile_name("React"), "React")

    def test_rejects_unsafe_payload_prefixes(self) -> None:
        for prefix in ("Private-", "private", "../", "private/tag-", "$(touch)-"):
            with self.subTest(prefix=prefix):
                self.assertTrue(any("release_payload_prefix" in error for error in validate({
                    "app_image": "ghcr.io/grumlebob/books",
                    "migration_bundle_name": "books-migrate",
                    "migration_runtime": "linux-x64",
                    "release_payload_prefix": prefix,
                })))

    def test_derived_fields_cannot_be_configured(self) -> None:
        errors = validate({
            "app_image": "ghcr.io/grumlebob/books",
            "migration_bundle_name": "books-migrate",
            "migration_runtime": "linux-x64",
            "release_payload_image": "ghcr.io/attacker/payload",
        })
        self.assertIn("unknown release setting: release_payload_image", errors)


if __name__ == "__main__":
    unittest.main()
