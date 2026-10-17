"""Read verified GHCR manifests and repository-linked package versions.

No layer bytes are downloaded or executed. Config blobs and manifests are
bounded and checked against their immutable descriptor hashes before use.
"""

from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import json
import re
from typing import Any, Mapping
import urllib.error
import urllib.parse
import urllib.request

from registry_payload import payload_tag
from registry_retention import ACTIVE, TERMINAL, DIGEST, PACKAGE, Inventory, Payload, RetentionError, Version


MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_VERSIONS = 10000
INDEX_TYPES = frozenset({"application/vnd.oci.image.index.v1+json", "application/vnd.docker.distribution.manifest.list.v2+json"})
IMAGE_TYPES = frozenset({"application/vnd.oci.image.manifest.v1+json", "application/vnd.docker.distribution.manifest.v2+json"})
MEDIA_TYPES = INDEX_TYPES | IMAGE_TYPES


def _json(raw: bytes) -> Any:
    if not isinstance(raw, bytes) or len(raw) > MAX_JSON_BYTES:
        raise RetentionError("registry JSON exceeds the inventory bound")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RetentionError("registry JSON contains duplicate keys")
            result[key] = value
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RetentionError("registry inventory JSON is malformed") from error


def _verified(raw: bytes, digest: str, length: int | None = None) -> Any:
    if not DIGEST.fullmatch(digest) or "sha256:" + hashlib.sha256(raw).hexdigest() != digest:
        raise RetentionError("registry content does not match its frozen digest")
    if length is not None and len(raw) != length:
        raise RetentionError("registry content length differs from its immutable descriptor")
    return _json(raw)


def _descriptor(value: Any) -> tuple[str, int]:
    if (not isinstance(value, dict) or not isinstance(value.get("digest"), str)
            or not DIGEST.fullmatch(value["digest"]) or type(value.get("size")) is not int
            or value["size"] < 0 or "urls" in value):
        raise RetentionError("registry descriptor identity, size or location is invalid")
    return value["digest"], value["size"]


class _CredentialSafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if urllib.parse.urlparse(newurl).scheme != "https":
            raise RetentionError("registry redirect must use HTTPS")
        redirected = super().redirect_request(request, fp, code, message, headers, newurl)
        if redirected is not None and urllib.parse.urlparse(newurl).netloc != urllib.parse.urlparse(request.full_url).netloc:
            redirected.remove_header("Authorization")
        return redirected


class RegistryClient:
    """An exact-host, bounded client using an existing short-lived workflow token."""

    def __init__(self, username: str, token: str):
        if not username or not token:
            raise RetentionError("existing registry credentials are required")
        self._username = username
        self._token = token
        self._bearers: dict[str, str] = {}
        self._opener = urllib.request.build_opener(_CredentialSafeRedirect())

    def _read(self, url: str, headers: dict[str, str], *, missing=False, method="GET") -> bytes | None:
        if method not in {"GET", "DELETE"}:
            raise RetentionError("unsupported registry maintenance request")
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=30) as response:
                value = response.read(MAX_JSON_BYTES + 1)
        except urllib.error.HTTPError as error:
            if missing and error.code == 404:
                return None
            raise RetentionError(f"registry inventory request failed with HTTP {error.code}") from None
        except (OSError, urllib.error.URLError) as error:
            raise RetentionError("registry inventory request is unavailable") from error
        if len(value) > MAX_JSON_BYTES:
            raise RetentionError("registry response exceeds the inventory bound")
        return value

    def github(self, path: str) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise RetentionError("GitHub inventory path is invalid")
        raw = self._read("https://api.github.com" + path, {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        })
        return _json(raw)

    def _registry(self, package: str, resource: str, digest: str) -> bytes:
        if not PACKAGE.fullmatch(package) or not DIGEST.fullmatch(digest) or resource not in {"manifests", "blobs"}:
            raise RetentionError("registry request must use an exact configured package and digest")
        name = package.removeprefix("ghcr.io/")
        if package not in self._bearers:
            query = urllib.parse.urlencode({"service": "ghcr.io", "scope": f"repository:{name}:pull"})
            basic = base64.b64encode(f"{self._username}:{self._token}".encode()).decode()
            response = _json(self._read("https://ghcr.io/token?" + query, {"Authorization": "Basic " + basic}))
            bearer = response.get("token") if isinstance(response, dict) else None
            if not isinstance(bearer, str) or not bearer:
                raise RetentionError("registry did not provide a scoped read token")
            self._bearers[package] = bearer
        return self._read(f"https://ghcr.io/v2/{name}/{resource}/{digest}", {
            "Authorization": "Bearer " + self._bearers[package], "Accept": ", ".join(sorted(MEDIA_TYPES)),
        })

    def manifest(self, package: str, digest: str) -> bytes:
        return self._registry(package, "manifests", digest)

    def config(self, package: str, digest: str) -> bytes:
        return self._registry(package, "blobs", digest)

    def _version_url(self, package: str, version_id: int) -> str:
        if not PACKAGE.fullmatch(package) or type(version_id) is not int or version_id <= 0:
            raise RetentionError("package deletion requires an exact payload package and positive version ID")
        owner, name = package.removeprefix("ghcr.io/").split("/", 1)
        return ("https://api.github.com/users/" + urllib.parse.quote(owner, safe="")
                + "/packages/container/" + urllib.parse.quote(name, safe="") + f"/versions/{version_id}")

    def version(self, package: str, version_id: int) -> dict | None:
        raw = self._read(self._version_url(package, version_id), {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        }, missing=True)
        return _json(raw) if raw is not None else None

    def delete_version(self, package: str, version_id: int) -> None:
        # This primitive provides no authority itself. The coordinated executor
        # checks and records its immutable reservation before calling it.
        self._read(self._version_url(package, version_id), {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        }, missing=True, method="DELETE")


def _source(labels: dict, repository: str) -> tuple[str, str, int, int, str]:
    source, ci_repository = labels.get("org.opencontainers.image.source"), labels.get("localcluster.ci.repository")
    if not isinstance(source, str) or not source or not isinstance(ci_repository, str) or not ci_repository:
        raise RetentionError("registry manifest has no complete CI payload ownership labels")
    if (source.casefold() != ("https://github.com/" + repository).casefold()
            or ci_repository.casefold() != repository.casefold()):
        raise RetentionError("registry payload belongs to a different repository")
    run_id, attempt = labels.get("localcluster.ci.run_id"), labels.get("localcluster.ci.run_attempt")
    revision = labels.get("org.opencontainers.image.revision")
    kind, profile = labels.get("io.github.release-payload.kind"), labels.get("io.github.release-payload.profile")
    if (not isinstance(run_id, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", run_id)
            or not isinstance(attempt, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", attempt)
            or not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision)
            or kind not in {"final", "staging", "harness"}
            or not isinstance(profile, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", profile)):
        raise RetentionError("registry payload producer labels are malformed")
    return kind, profile, int(run_id), int(attempt), revision


def collect_inventory(
    repository: str,
    packages: Mapping[str, str],
    client: RegistryClient,
    *,
    retained_manifests: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[Inventory, dict[tuple[int, int], str]]:
    """Verify package linkage, complete manifest graphs and exact CI attempts."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not packages:
        raise RetentionError("an exact repository and configured payload packages are required")
    versions = []
    payloads = []
    states = {}
    owner = repository.split("/")[0]
    if (len(retained_manifests) > 100 or any(
            package not in packages or not DIGEST.fullmatch(digest)
            for package, digest in retained_manifests)):
        raise RetentionError("retained bootstrap references must name exact configured packages and digests")
    for package, visibility in sorted(packages.items()):
        if not PACKAGE.fullmatch(package) or visibility not in {"private", "public", "internal"}:
            raise RetentionError("configured package identity or visibility is invalid")
        registry_owner, name = package.removeprefix("ghcr.io/").split("/", 1)
        if registry_owner.casefold() != owner.casefold():
            raise RetentionError("registry package owner differs from the repository owner")
        # The /users/{username} endpoint only exposes public package metadata.
        # The authenticated-user endpoint supports private packages and Actions tokens.
        path = f"/user/packages/container/{urllib.parse.quote(name, safe='')}"
        metadata = client.github(path)
        if (not isinstance(metadata, dict) or metadata.get("name") != name
                or metadata.get("visibility") != visibility):
            raise RetentionError("registry package name or visibility differs from the configured owner")
        package_owner = metadata.get("owner")
        if (not isinstance(package_owner, dict) or not isinstance(package_owner.get("login"), str)
                or package_owner["login"].casefold() != owner.casefold()):
            raise RetentionError("registry package owner differs from the configured owner")
        linked_repository = metadata.get("repository")
        if linked_repository is not None and (
                not isinstance(linked_repository, dict)
                or not isinstance(linked_repository.get("full_name"), str)
                or linked_repository["full_name"].casefold() != repository.casefold()):
            raise RetentionError("registry package is linked to a different repository")
        # The owner-scoped package endpoint may omit repository linkage details
        # for a repository-scoped workflow token. Any payload root is still
        # required below to match this repository's exact OCI source labels and
        # a successful CI run attempt from this repository.
        raw_versions = []
        for page in range(1, MAX_VERSIONS // 100 + 1):
            batch = client.github(f"{path}/versions?per_page=100&page={page}")
            if not isinstance(batch, list) or len(batch) > 100:
                raise RetentionError("package version page is malformed")
            raw_versions.extend(batch)
            if len(batch) < 100:
                break
        else:
            raise RetentionError("package inventory exceeds the bounded page limit")
        package_versions = {}
        labels_by_digest = {}
        descriptor_sizes = {}
        for item in raw_versions:
            if (not isinstance(item, dict) or not isinstance(item.get("name"), str) or not DIGEST.fullmatch(item["name"])
                    or type(item.get("id")) is not int or item["id"] <= 0):
                raise RetentionError("package version has no immutable manifest digest")
            digest = item["name"]
            if digest in package_versions:
                raise RetentionError("package inventory contains a duplicate manifest digest")
            raw = client.manifest(package, digest)
            manifest = _verified(raw, digest)
            if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 2 or manifest.get("mediaType") not in MEDIA_TYPES:
                raise RetentionError("registry manifest format is unsupported")
            children = []
            blobs = []
            if manifest["mediaType"] in INDEX_TYPES:
                if not isinstance(manifest.get("manifests"), list) or not manifest["manifests"]:
                    raise RetentionError("registry index has no manifest descriptors")
                for descriptor in manifest["manifests"]:
                    child_digest, length = _descriptor(descriptor)
                    children.append(child_digest)
                    if child_digest in descriptor_sizes and descriptor_sizes[child_digest] != length:
                        raise RetentionError("registry child manifest sizes conflict")
                    descriptor_sizes[child_digest] = length
            else:
                config_digest, length = _descriptor(manifest.get("config"))
                config = _verified(client.config(package, config_digest), config_digest, length)
                if not isinstance(config, dict) or not isinstance(manifest.get("layers"), list):
                    raise RetentionError("registry image config or layers are malformed")
                runtime = config.get("config")
                labels = runtime.get("Labels") if isinstance(runtime, dict) else None
                if labels is not None:
                    if not isinstance(labels, dict) or any(not isinstance(value, str) for value in labels.values()):
                        raise RetentionError("registry config labels are malformed")
                    # BuildKit attestation configs can contain an empty Labels
                    # object. Only their owning parent payload provides source
                    # identity; an unlabeled standalone root still fails below.
                    if labels:
                        labels_by_digest[digest] = labels
                blobs = [(config_digest, length), *[_descriptor(value) for value in manifest["layers"]]]
            tags = item.get("metadata", {}).get("container", {}).get("tags")
            if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag for tag in tags):
                raise RetentionError("registry version tags are malformed")
            if len(tags) != len(set(tags)) or len(children) != len(set(children)):
                raise RetentionError("registry version contains duplicate tags or children")
            try:
                created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            except (KeyError, AttributeError, TypeError, ValueError) as error:
                raise RetentionError("registry version creation timestamp is invalid") from error
            version = Version(package, item.get("id"), digest, frozenset(tags), created, frozenset(children), tuple(blobs), len(raw))
            package_versions[digest] = version
        for digest, length in descriptor_sizes.items():
            if digest not in package_versions or package_versions[digest].manifest_bytes != length:
                raise RetentionError("registry index references a missing or differently sized manifest")
        descendants = {child for version in package_versions.values() for child in version.children}
        roots = set(package_versions) - descendants

        def source_identities(digest, visiting=frozenset()):
            if digest in visiting or digest not in package_versions:
                raise RetentionError("registry manifest graph is cyclic or incomplete")
            identities = set()
            if digest in labels_by_digest:
                try:
                    identities.add(_source(labels_by_digest[digest], repository))
                except RetentionError as error:
                    raise RetentionError(f"{package}@{digest}: {error}") from error
            for child in package_versions[digest].children:
                identities.update(source_identities(child, visiting | {digest}))
            return identities

        for digest in sorted(roots):
            if (package, digest) in retained_manifests:
                version = package_versions[digest]
                if (version.children or len(version.blobs) != 1
                        or version.manifest_bytes + sum(size for _, size in version.blobs) > 65536):
                    raise RetentionError("retained bootstrap must be a bounded config-only manifest")
                continue
            identities = source_identities(digest)
            if len(identities) != 1:
                raise RetentionError("registry root has unknown or conflicting payload ownership")
            kind, profile, run_id, attempt, revision = identities.pop()
            expected_tag = payload_tag(str(run_id), str(attempt), profile, kind=kind)
            visited = set()

            def validate_tags(value):
                if value in visited:
                    return
                visited.add(value)
                version = package_versions[value]
                if version.tags - {expected_tag}:
                    raise RetentionError("registry payload has an unknown referencing tag")
                for child in version.children:
                    validate_tags(child)

            validate_tags(digest)
            run = client.github(f"/repos/{repository}/actions/runs/{run_id}/attempts/{attempt}")
            if (not isinstance(run, dict) or run.get("id") != run_id or run.get("run_attempt") != attempt
                    or run.get("head_sha") != revision or run.get("head_branch") != "main"
                    or run.get("status") not in ACTIVE | TERMINAL
                    or run.get("event") not in {"push", "workflow_dispatch"}
                    or str(run.get("path", "")).split("@", 1)[0] != ".github/workflows/ci.yml"
                    or not isinstance(run.get("head_repository"), dict)
                    or run["head_repository"].get("full_name", "").casefold() != repository.casefold()):
                raise RetentionError("registry producer labels do not match the exact trusted CI attempt")
            identity = run_id, attempt
            if identity in states and states[identity] != run.get("status"):
                raise RetentionError("CI state changed during inventory; obtain a fresh snapshot")
            states[identity] = run.get("status")
            version = package_versions[digest]
            payloads.append(Payload(package, digest, kind, profile, run_id, attempt, version.created, revision))
        versions.extend(package_versions.values())
    result = Inventory(repository, tuple(versions), tuple(payloads), frozenset(packages), True, retained_manifests)
    # Also reject missing references and references to a payload descendant.
    from registry_retention import inventory_usage
    inventory_usage(result)
    return result, states
