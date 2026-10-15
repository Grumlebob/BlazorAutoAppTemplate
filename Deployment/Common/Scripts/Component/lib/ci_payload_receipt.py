from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable

from release_settings import derive_release_payload_image, validate_app_image, validate_profile_name
from registry_payload import (
    DIGEST_RE,
    MANIFEST_FILENAME,
    PAYLOAD_KINDS,
    ReleasePayloadIdentity,
    content_checksum,
)


RECEIPT_PREFIX = "RELEASE_PAYLOAD_RECEIPT_V1 "
RECEIPT_COMMAND_MARKER = "##[group]Run python3 Scripts/CI/emit_release_payload_receipt.py"
API_VERSION = "2026-03-10"
MAX_JOB_LOG_BYTES = 64 * 1024 * 1024
SHA_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
ID_RE = re.compile(r"[1-9][0-9]{0,19}\Z")
TIMESTAMP_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z) (?P<message>.*)$"
)
REPOSITORY_RE = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")

COMMON_FIELDS = frozenset(
    {
        "schema_version",
        "kind",
        "repository",
        "sha",
        "run_id",
        "run_attempt",
        "profile",
        "runtime",
        "payload_image",
        "payload_ref",
        "payload_digest",
        "content_sha256",
    }
)
FINAL_REQUIRED_FIELDS = frozenset(
    {
        "app_image",
        "app_image_digest",
        "manifest_sha256",
    }
)
FINAL_OPTIONAL_FIELDS = frozenset({"acceptance_profile", "bundle_filename", "bundle_sha256"})


class ReceiptError(ValueError):
    """Raised when a CI payload receipt is missing or does not match trusted provenance."""


def final_receipt(identity: ReleasePayloadIdentity, published: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(published, dict):
        raise ReceiptError("registry publication result must be an object")
    expected_image = derive_release_payload_image(identity.app_image)
    digest = published.get("payload_digest")
    payload_ref = f"{expected_image}@{digest}" if isinstance(digest, str) else ""
    content_files = {MANIFEST_FILENAME: identity.manifest_sha256}
    receipt = {
        "schema_version": 1,
        "kind": "final",
        "repository": identity.repository,
        "sha": identity.commit_sha,
        "run_id": identity.run_id,
        "run_attempt": identity.run_attempt,
        "profile": identity.profile,
        "runtime": identity.runtime,
        "payload_image": expected_image,
        "payload_ref": payload_ref,
        "payload_digest": digest,
        "content_sha256": "",
        "app_image": identity.app_image,
        "app_image_digest": identity.app_image_digest,
        "manifest_sha256": identity.manifest_sha256,
    }
    if identity.acceptance_profile is not None:
        receipt["acceptance_profile"] = identity.acceptance_profile
    if identity.bundle_filename is not None and identity.bundle_sha256 is not None:
        content_files[identity.bundle_filename] = identity.bundle_sha256
        receipt["bundle_filename"] = identity.bundle_filename
        receipt["bundle_sha256"] = identity.bundle_sha256
    receipt["content_sha256"] = content_checksum(content_files)
    expected_published = {
        "kind": "final",
        "payload_image": expected_image,
        "payload_ref": payload_ref,
        "payload_digest": digest,
        "repository": identity.repository,
        "commit_sha": identity.commit_sha,
        "run_id": identity.run_id,
        "run_attempt": identity.run_attempt,
        "profile": identity.profile,
        "acceptance_profile": identity.acceptance_profile,
        "runtime": identity.runtime,
        "content_sha256": receipt["content_sha256"],
        "manifest_sha256": identity.manifest_sha256,
        "bundle_filename": identity.bundle_filename,
        "bundle_sha256": identity.bundle_sha256,
        "app_image": identity.app_image,
        "app_image_digest": identity.app_image_digest,
    }
    for key, expected in expected_published.items():
        if published.get(key) != expected:
            raise ReceiptError(f"registry publication result {key!r} does not match the frozen release")
    return validate_receipt(receipt)


def validate_receipt(receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise ReceiptError("payload receipt must be a JSON object")
    kind = receipt.get("kind")
    if not isinstance(kind, str) or kind not in PAYLOAD_KINDS:
        raise ReceiptError("payload receipt kind is unsupported")
    required_fields = COMMON_FIELDS | (FINAL_REQUIRED_FIELDS if kind == "final" else frozenset())
    allowed_fields = required_fields | (FINAL_OPTIONAL_FIELDS if kind == "final" else frozenset())
    if not required_fields.issubset(receipt) or not set(receipt).issubset(allowed_fields):
        missing = sorted(required_fields.difference(receipt))
        extra = sorted(set(receipt).difference(allowed_fields))
        raise ReceiptError(f"payload receipt fields are invalid; missing={missing}, extra={extra}")
    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
        raise ReceiptError("payload receipt schema version is unsupported")
    if not isinstance(receipt["repository"], str) or not REPOSITORY_RE.fullmatch(receipt["repository"]):
        raise ReceiptError("payload receipt repository is invalid")
    if not isinstance(receipt["sha"], str) or not SHA_RE.fullmatch(receipt["sha"]):
        raise ReceiptError("payload receipt SHA must be a full lowercase hexadecimal SHA")
    for field in ("run_id", "run_attempt"):
        if not isinstance(receipt[field], str) or not ID_RE.fullmatch(receipt[field]):
            raise ReceiptError(f"payload receipt {field} must be a positive decimal value")
    try:
        validate_profile_name(receipt["profile"])
    except (TypeError, ValueError) as error:
        raise ReceiptError("payload receipt profile is unsafe") from error
    if not isinstance(receipt["runtime"], str) or receipt["runtime"] not in {"linux-x64", "linux-arm64"}:
        raise ReceiptError("payload receipt runtime is unsupported")
    try:
        payload_image = validate_app_image(receipt["payload_image"])
    except (AttributeError, TypeError, ValueError) as error:
        raise ReceiptError("payload receipt image path is invalid") from error
    digest = receipt["payload_digest"]
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        raise ReceiptError("payload receipt registry digest is invalid")
    if receipt["payload_ref"] != f"{payload_image}@{digest}":
        raise ReceiptError("payload receipt reference does not equal its frozen image and digest")
    if not isinstance(receipt["content_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", receipt["content_sha256"]):
        raise ReceiptError("payload receipt content checksum is invalid")

    if kind == "final":
        if ("bundle_filename" in receipt) != ("bundle_sha256" in receipt):
            raise ReceiptError("final payload receipt must include both bundle filename and checksum")
        try:
            app_image = validate_app_image(receipt["app_image"])
            if "acceptance_profile" in receipt:
                validate_profile_name(receipt["acceptance_profile"])
        except (AttributeError, TypeError, ValueError) as error:
            raise ReceiptError("final payload receipt application image or acceptance profile is invalid") from error
        if payload_image != derive_release_payload_image(app_image):
            raise ReceiptError("final payload image is not derived from its application image")
        if not isinstance(receipt["app_image_digest"], str) or not DIGEST_RE.fullmatch(receipt["app_image_digest"]):
            raise ReceiptError("final payload application image digest is invalid")
        if not isinstance(receipt["manifest_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", receipt["manifest_sha256"]):
            raise ReceiptError("final payload manifest_sha256 is invalid")
        content_files = {MANIFEST_FILENAME: receipt["manifest_sha256"]}
        if "bundle_filename" in receipt:
            bundle_name = receipt["bundle_filename"]
            if (
                not isinstance(bundle_name, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", bundle_name)
                or bundle_name == MANIFEST_FILENAME
            ):
                raise ReceiptError("final payload bundle filename is unsafe")
            if not isinstance(receipt["bundle_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", receipt["bundle_sha256"]):
                raise ReceiptError("final payload bundle_sha256 is invalid")
            content_files[bundle_name] = receipt["bundle_sha256"]
        expected_content = content_checksum(content_files)
        if receipt["content_sha256"] != expected_content:
            raise ReceiptError("final payload content checksum does not match manifest and bundle hashes")
    return dict(receipt)


def format_receipt_line(receipt: Any) -> str:
    valid = validate_receipt(receipt)
    return RECEIPT_PREFIX + json.dumps(valid, sort_keys=True, separators=(",", ":"))


def parse_receipt_line(line: str) -> dict[str, Any]:
    if not isinstance(line, str) or not line.startswith(RECEIPT_PREFIX):
        raise ReceiptError("CI log line is not a release payload receipt")
    try:
        payload = json.loads(line[len(RECEIPT_PREFIX):])
    except json.JSONDecodeError as error:
        raise ReceiptError("CI release payload receipt is malformed JSON") from error
    return validate_receipt(payload)


def _parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReceiptError(f"CI {field} timestamp is missing or not UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as error:
        raise ReceiptError(f"CI {field} timestamp is invalid") from error


def receipts_from_step_log(
    job: Any,
    log_text: str,
    *,
    step_name: str,
    expected_job_name: str,
    expected_run_id: str,
    expected_run_attempt: str,
    expected_sha: str,
) -> list[dict[str, Any]]:
    """Read receipts only from one successful, exact-run job step's timestamp range."""
    if not isinstance(job, dict) or job.get("name") != expected_job_name:
        raise ReceiptError("receipt job name does not match the expected publisher job")
    job_identity = {
        "run_id": expected_run_id,
        "run_attempt": expected_run_attempt,
        "head_sha": expected_sha,
    }
    for field, expected in job_identity.items():
        if str(job.get(field, "")) != str(expected):
            raise ReceiptError(f"receipt job {field} does not match the selected CI attempt")
    if job.get("status") != "completed" or job.get("conclusion") != "success":
        raise ReceiptError("receipt job did not complete successfully")
    steps = job.get("steps")
    if not isinstance(steps, list) or any(not isinstance(step, dict) for step in steps):
        raise ReceiptError("receipt job step metadata is malformed")
    matches = [step for step in steps if step.get("name") == step_name]
    if len(matches) != 1:
        raise ReceiptError("expected exactly one immutable payload receipt step in the selected job")
    step = matches[0]
    if step.get("status") != "completed" or step.get("conclusion") != "success":
        raise ReceiptError("immutable payload receipt step did not complete successfully")
    completed_at = step.get("completed_at")
    start = _parse_timestamp(step.get("started_at"), "receipt step start")
    end = _parse_timestamp(completed_at, "receipt step completion")
    if end < start:
        raise ReceiptError("receipt step time range is reversed")
    # The Actions API reports step timestamps at whole-second precision while
    # log lines may include fractions. Include that final reported second; the
    # next ##[group] marker still closes this step's trusted command window.
    end_exclusive = (
        end + timedelta(seconds=1)
        if isinstance(completed_at, str) and "." not in completed_at
        else end
    )
    if not isinstance(log_text, str) or not log_text:
        raise ReceiptError("selected CI job logs are unavailable or expired")

    found: list[dict[str, Any]] = []
    in_receipt_step_command = False
    command_markers = 0
    for raw_line in log_text.removeprefix("\ufeff").splitlines():
        match = TIMESTAMP_LINE_RE.match(raw_line)
        if not match:
            continue
        timestamp = _parse_timestamp(match.group("timestamp"), "job log line")
        if not start <= timestamp < end_exclusive:
            continue
        message = match.group("message")
        if message.startswith(RECEIPT_COMMAND_MARKER):
            command_markers += 1
            in_receipt_step_command = True
            continue
        if in_receipt_step_command and message.startswith("##[group]"):
            in_receipt_step_command = False
        if message.startswith(RECEIPT_PREFIX):
            if in_receipt_step_command:
                found.append(parse_receipt_line(message))
    if command_markers != 1:
        raise ReceiptError("selected receipt step does not contain exactly one trusted emitter command")
    identities: set[tuple[str, str]] = set()
    for receipt in found:
        identity = (receipt["kind"], receipt["profile"])
        if identity in identities:
            raise ReceiptError("duplicate release payload receipt for the same kind and profile")
        identities.add(identity)
        for field, expected in (
            ("run_id", expected_run_id),
            ("run_attempt", expected_run_attempt),
            ("sha", expected_sha),
        ):
            if receipt[field] != str(expected):
                raise ReceiptError(f"receipt {field} does not match the selected CI attempt")
    if not found:
        raise ReceiptError("selected successful receipt step contains no valid payload receipt")
    return found


def select_receipt(receipts: Iterable[dict[str, Any]], expected: dict[str, str]) -> dict[str, Any]:
    if not isinstance(expected, dict) or not expected:
        raise ReceiptError("expected receipt identity is required")
    matches = []
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ReceiptError("receipt collection contains malformed data")
        if all(receipt.get(field) == value for field, value in expected.items()):
            matches.append(receipt)
    if len(matches) != 1:
        raise ReceiptError("expected exactly one receipt matching the selected payload identity")
    return validate_receipt(matches[0])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download_job_logs(
    repository: str,
    job_id: int,
    token: str,
    *,
    api_root: str = "https://api.github.com",
    max_bytes: int = MAX_JOB_LOG_BYTES,
) -> str:
    """Fetch logs through the authenticated API, then follow its signed URL without credentials."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ReceiptError("repository must be owner/name")
    if type(job_id) is not int or job_id < 1:
        raise ReceiptError("job ID must be a positive integer")
    if not isinstance(token, str) or not token.strip():
        raise ReceiptError("GITHUB_TOKEN is required to read CI job logs")
    if type(max_bytes) is not int or max_bytes < 1:
        raise ReceiptError("job log byte limit is invalid")

    root = api_root.rstrip("/")
    endpoint = f"{root}/repos/{repository}/actions/jobs/{job_id}/logs"
    request = urllib.request.Request(
        endpoint,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token.strip()}",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    try:
        try:
            response = urllib.request.build_opener(_NoRedirect).open(request, timeout=30)
        except urllib.error.HTTPError as error:
            if error.code != 302 or not error.headers.get("Location"):
                raise ReceiptError(f"GitHub job logs are unavailable (HTTP {error.code})") from error
            signed_url = error.headers["Location"]
            parsed = urllib.parse.urlparse(signed_url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ReceiptError("GitHub returned an unsafe job log redirect")
            response = urllib.request.urlopen(urllib.request.Request(signed_url), timeout=60)
        with response:
            data = response.read(max_bytes + 1)
    except ReceiptError:
        raise
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
        raise ReceiptError("GitHub job logs could not be downloaded") from error
    if len(data) > max_bytes:
        raise ReceiptError("GitHub job log exceeds the configured size limit")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ReceiptError("GitHub job log is not valid UTF-8 text") from error


def expected_final_identity(
    *,
    repository: str,
    commit_sha: str,
    run_id: str,
    run_attempt: str,
    profile: str,
    acceptance_profile: str | None = None,
    runtime: str,
    app_image: str,
) -> dict[str, str]:
    try:
        expected_image = derive_release_payload_image(app_image)
        validate_profile_name(profile)
        if acceptance_profile is not None:
            validate_profile_name(acceptance_profile)
    except (AttributeError, TypeError, ValueError) as error:
        raise ReceiptError("expected final receipt identity is invalid") from error
    expected = {
        "kind": "final",
        "repository": repository,
        "sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "profile": profile,
        "runtime": runtime,
        "payload_image": expected_image,
    }
    if acceptance_profile is not None:
        expected["acceptance_profile"] = acceptance_profile
    return expected
