from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
import urllib.request


LIB = Path(__file__).resolve().parents[1] / "Component/lib"
sys.path.insert(0, str(LIB))
import registry_inventory as inventory
import registry_retention as retention


PACKAGE = "ghcr.io/example/app-release-payload"
REPOSITORY = "example/app"


def encode(value):
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest(), raw


class FixtureClient:
    def __init__(self):
        self.labels = {
            "org.opencontainers.image.source": "https://github.com/example/app",
            "org.opencontainers.image.revision": "a" * 40,
            "localcluster.ci.repository": REPOSITORY,
            "localcluster.ci.run_id": "101", "localcluster.ci.run_attempt": "1",
            "io.github.release-payload.kind": "final", "io.github.release-payload.profile": "React",
        }
        self.run = {
            "id": 101, "run_attempt": 1, "head_sha": "a" * 40, "head_branch": "main",
            "event": "push", "path": ".github/workflows/ci.yml", "status": "completed",
            "head_repository": {"full_name": REPOSITORY},
        }
        self.metadata = {
            "name": "app-release-payload", "visibility": "private",
            "owner": {"login": "example"}, "repository": {"full_name": REPOSITORY},
        }
        self.calls = []
        self.attestation_config = {}
        self.rebuild()

    def rebuild(self):
        config_digest, config = encode({"config": {"Labels": self.labels}})
        empty_digest, empty = encode(self.attestation_config)
        self.configs = {config_digest: config, empty_digest: empty}
        leaf_digest, leaf = encode({
            "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": config_digest, "size": len(config)},
            "layers": [{"digest": "sha256:" + "b" * 64, "size": 123}],
        })
        attest_digest, attest = encode({
            "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": empty_digest, "size": len(empty)},
            "layers": [{"digest": "sha256:" + "c" * 64, "size": 45}],
        })
        parent_digest, parent = encode({
            "schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [{"digest": leaf_digest, "size": len(leaf)}, {"digest": attest_digest, "size": len(attest)}],
        })
        self.manifests = {parent_digest: parent, leaf_digest: leaf, attest_digest: attest}
        self.versions = [{
            "id": number, "name": digest, "created_at": "2026-10-10T00:00:00Z",
            "metadata": {"container": {"tags": ["run-101-attempt-1-kind-final-profile-react"] if number == 1 else []}},
        } for number, digest in enumerate(self.manifests, 1)]

    def github(self, path):
        self.calls.append(path)
        if path.endswith("/attempts/1"):
            return deepcopy(self.run)
        if "/versions?" in path:
            return deepcopy(self.versions)
        return deepcopy(self.metadata)

    def manifest(self, package, digest):
        if package != PACKAGE:
            raise AssertionError("Unexpected package")
        self.calls.append("manifest:" + digest)
        return self.manifests[digest]

    def config(self, package, digest):
        if package != PACKAGE:
            raise AssertionError("Unexpected package")
        self.calls.append("config:" + digest)
        return self.configs[digest]

    def add_bootstrap(self, *, layers=None, padding=""):
        config_digest, config = encode({"config": {"Labels": {"org.opencontainers.image.title": "bootstrap"}}, "padding": padding})
        digest, raw = encode({
            "schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": config_digest, "size": len(config)}, "layers": layers or [],
        })
        self.configs[config_digest] = config
        self.manifests[digest] = raw
        self.versions.append({"id": 90, "name": digest, "created_at": "2026-10-01T00:00:00Z",
                              "metadata": {"container": {"tags": ["bootstrap-reviewed"]}}})
        return PACKAGE, digest


class RegistryInventoryTests(unittest.TestCase):
    def test_explicit_config_only_bootstrap_is_counted_protected_and_never_fakes_ci_provenance(self):
        client = FixtureClient()
        reference = client.add_bootstrap()
        value, states = inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client,
                                                     retained_manifests=frozenset({reference}))
        self.assertEqual(4, len(value.versions))
        self.assertEqual(1, len(value.payloads))
        self.assertEqual({(101, 1): "completed"}, states)
        self.assertEqual(value, retention.inventory_from_record(retention.inventory_record(value)))
        usage = retention.inventory_usage(value)
        self.assertGreater(usage["retained_manifest_bytes"], 0)
        self.assertEqual(usage["final_bytes"] + usage["retained_manifest_bytes"], usage["total_bytes"])
        references = retention.Protection(frozenset(), frozenset(), frozenset(), states, True)
        plan = retention.plan_retention(value, references, now=retention.datetime(2026, 10, 20, tzinfo=retention.timezone.utc))
        self.assertEqual({1, 2, 3}, {item.version_id for item in plan.delete})
        self.assertEqual(usage["retained_manifest_bytes"], plan.protected_bytes)

    def test_bootstrap_without_an_exact_reviewed_reference_still_stops_inventory(self):
        client = FixtureClient()
        reference = client.add_bootstrap()
        for retained in (frozenset(), frozenset({(PACKAGE, "sha256:" + "f" * 64)}),
                         frozenset({("ghcr.io/foreign/app-release-payload", reference[1])})):
            with self.subTest(retained=retained), self.assertRaises(retention.RetentionError):
                inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client, retained_manifests=retained)

    def test_retained_bootstrap_cannot_hide_layers_large_configs_or_payload_children(self):
        for parameters in ({"layers": [{"digest": "sha256:" + "d" * 64, "size": 12}]}, {"padding": "x" * 65536}):
            client = FixtureClient()
            reference = client.add_bootstrap(**parameters)
            with self.subTest(parameters=tuple(parameters)), self.assertRaises(retention.RetentionError):
                inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client, retained_manifests=frozenset({reference}))
        client = FixtureClient()
        child = PACKAGE, client.versions[1]["name"]
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client, retained_manifests=frozenset({child}))

    def test_empty_attestation_labels_use_parent_ownership_but_foreign_child_labels_are_rejected(self):
        client = FixtureClient()
        client.attestation_config = {"config": {"Labels": {}}}
        client.rebuild()
        value, _ = inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)
        self.assertEqual(1, len(value.payloads))
        self.assertEqual(3, len(value.versions))
        client.attestation_config = {"config": {"Labels": {"org.opencontainers.image.source": "https://github.com/foreign/app"}}}
        client.rebuild()
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)

    def test_reads_parent_image_and_attestation_by_verified_digest_without_layer_downloads(self):
        client = FixtureClient()
        value, states = inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)
        self.assertEqual(3, len(value.versions))
        self.assertEqual(1, len(value.payloads))
        self.assertEqual("a" * 40, value.payloads[0].commit_sha)
        self.assertEqual({(101, 1): "completed"}, states)
        self.assertIn("/repos/example/app/actions/runs/101/attempts/1", client.calls)
        self.assertEqual(2, len([call for call in client.calls if call.startswith("config:")]))
        references = retention.Protection(frozenset(), frozenset(), frozenset(), states, True)
        plan = retention.plan_retention(value, references, now=retention.datetime(2026, 10, 20, tzinfo=retention.timezone.utc))
        self.assertEqual(3, len(plan.delete))
        self.assertEqual(value.payloads[0].digest, plan.delete[0].digest)

    def test_visibility_and_repository_linkage_are_checked_before_manifest_access(self):
        for field, replacement in (("visibility", "public"), ("repository", {"full_name": "foreign/app"}),
                                   ("repository", {"full_name": None}), ("name", "other-release-payload")):
            client = FixtureClient()
            client.metadata[field] = replacement
            with self.subTest(field=field), self.assertRaises(retention.RetentionError):
                inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)
            self.assertFalse(any(call.startswith("manifest:") for call in client.calls))

    def test_private_package_metadata_uses_authenticated_user_endpoint_and_checks_owner(self):
        client = FixtureClient()
        inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)
        self.assertEqual("/user/packages/container/app-release-payload", client.calls[0])

        client = FixtureClient()
        client.metadata["owner"] = {"login": "foreign"}
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)
        self.assertEqual("/user/packages/container/app-release-payload", client.calls[0])
        self.assertFalse(any(call.startswith("manifest:") for call in client.calls))

    def test_omitted_or_unavailable_repository_linkage_keeps_exact_payload_provenance_checks(self):
        for linkage in ("omitted", None):
            client = FixtureClient()
            if linkage == "omitted":
                del client.metadata["repository"]
            else:
                client.metadata["repository"] = linkage
            value, _ = inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)
            self.assertEqual(1, len(value.payloads))
            self.assertEqual(REPOSITORY, value.repository)

        client = FixtureClient()
        del client.metadata["repository"]
        client.labels["localcluster.ci.repository"] = "foreign/app"
        client.rebuild()
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)

    def test_exact_attempt_sha_main_ref_workflow_and_repository_must_match_labels(self):
        for field, replacement in (
            ("run_attempt", 2), ("head_sha", "d" * 40), ("head_branch", "feature"),
            ("event", "pull_request"), ("path", ".github/workflows/unrelated.yml"),
            ("head_repository", {"full_name": "foreign/app"}), ("status", "unknown"),
        ):
            client = FixtureClient()
            client.run[field] = replacement
            with self.subTest(field=field), self.assertRaises(retention.RetentionError):
                inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)

    def test_forged_repository_labels_are_rejected_even_in_a_linked_package(self):
        client = FixtureClient()
        client.labels["org.opencontainers.image.source"] = "https://github.com/foreign/app"
        client.rebuild()
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)

    def test_unknown_alias_or_tag_on_an_untagged_child_stops_inventory(self):
        for version_index in (0, 1):
            client = FixtureClient()
            client.versions[version_index]["metadata"]["container"]["tags"].append("manual-alias")
            with self.subTest(version_index=version_index), self.assertRaises(retention.RetentionError):
                inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)

    def test_missing_child_and_unowned_orphan_are_rejected(self):
        client = FixtureClient()
        client.versions.pop()
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)
        client = FixtureClient()
        client.versions = [client.versions[-1]]
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)

    def test_manifest_hash_and_config_hash_are_verified(self):
        client = FixtureClient()
        key = next(iter(client.manifests))
        client.manifests[key] += b" "
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)
        client = FixtureClient()
        key = next(iter(client.configs))
        client.configs[key] += b" "
        with self.assertRaises(retention.RetentionError):
            inventory.collect_inventory(REPOSITORY, {PACKAGE: "private"}, client)

    def test_duplicate_json_keys_and_large_responses_are_rejected(self):
        for raw in (b'{"name":1,"name":2}', b" " * (inventory.MAX_JSON_BYTES + 1)):
            with self.subTest(length=len(raw)), self.assertRaises(retention.RetentionError):
                inventory._json(raw)

    def test_descriptor_cannot_redirect_reads_or_supply_unknown_byte_sizes(self):
        for descriptor in (
            {"digest": "sha256:" + "1" * 64, "size": True},
            {"digest": "sha256:" + "1" * 64, "size": -1},
            {"digest": "sha256:" + "1" * 64, "size": 10, "urls": ["https://foreign.example/blob"]},
        ):
            with self.subTest(descriptor=descriptor), self.assertRaises(retention.RetentionError):
                inventory._descriptor(descriptor)

    def test_redirect_does_not_forward_credentials_to_another_host_or_allow_http(self):
        handler = inventory._CredentialSafeRedirect()
        request = urllib.request.Request("https://ghcr.io/v2/example/app/blobs/sha256:abc", headers={"Authorization": "Bearer fixture-only"})
        redirected = handler.redirect_request(request, None, 302, "Found", {}, "https://cdn.example/blob")
        self.assertIsNone(redirected.get_header("Authorization"))
        with self.assertRaises(retention.RetentionError):
            handler.redirect_request(request, None, 302, "Found", {}, "http://cdn.example/blob")


if __name__ == "__main__":
    unittest.main()
