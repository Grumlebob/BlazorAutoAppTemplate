#!/usr/bin/env python3
"""Select one explicitly configured CI profile from a fresh repository snapshot.

Selection is not a reservation or migration of an assigned job. Runtime identity
verification remains mandatory on the actual worker before privileged steps.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    from Scripts.CI.runner_profiles import ProfileError, RunnerProfile, load_profiles, select_profile
except ModuleNotFoundError:
    from runner_profiles import ProfileError, RunnerProfile, load_profiles, select_profile

API_VERSION = "2026-03-10"
API_ROOT = "https://api.github.com"
PAGE_SIZE = 100
MAX_PAGES = 100
MAX_RESPONSE_BYTES = 2 * 1024**2
PLATFORM_LABELS = frozenset({"self-hosted", "linux", "x64"})


class RunnerSelectionError(ValueError):
    pass


class InventoryUnavailable(RunnerSelectionError):
    """A bounded, credential-free reason for configured native fallback."""


def ci_label(profile: RunnerProfile, label: str) -> str:
    if label not in profile.labels or re.search(
        r"(^|-)(deploy|deployment|cd|localcluster|localsinglenode)(-|$)", label, re.IGNORECASE,
    ):
        raise RunnerSelectionError("Scheduling label is outside the profile's approved CI labels")
    return label


@dataclass(frozen=True)
class RoutingPolicy:
    repository: str
    native: RunnerProfile
    native_label: str
    desktop: RunnerProfile | None = None

    def __post_init__(self):
        if self.native.kind != "native" or self.native.repository != self.repository:
            raise RunnerSelectionError("An explicit native profile for this repository is required")
        ci_label(self.native, self.native_label)
        if self.desktop is not None:
            if self.desktop.kind != "desktop" or self.desktop.repository != self.repository:
                raise RunnerSelectionError("Desktop registration must belong to this repository")
            if self.desktop.runner_name == self.native.runner_name:
                raise RunnerSelectionError("Native and desktop registrations must be distinct")
            for suffix in ("-desktop", "-canary"):
                candidates = [label for label in self.desktop.labels if label.endswith(suffix)]
                if len(candidates) != 1 or candidates[0].casefold() == self.native_label.casefold():
                    raise RunnerSelectionError("Desktop and canary routes need distinct explicit labels")
                ci_label(self.desktop, candidates[0])

    def desktop_label(self, *, canary: bool = False) -> str:
        if self.desktop is None:
            raise RunnerSelectionError("No desktop profile is configured for this repository")
        suffix = "-canary" if canary else "-desktop"
        return next(label for label in self.desktop.labels if label.endswith(suffix))

    def approve_selector(self, name: str) -> None:
        names = {self.native.runner_name}
        if self.desktop is not None:
            names.add(self.desktop.runner_name)
        if name not in names:
            raise RunnerSelectionError("Selector identity is outside the approved CI profiles")


@dataclass(frozen=True)
class WorkflowContext:
    repository: str
    event: str
    ref: str
    head_repository: str | None = None
    base_repository: str | None = None

    def validate(self, *, stage: str, requested_pool: str) -> None:
        if self.event not in {"pull_request", "push", "workflow_dispatch"}:
            raise RunnerSelectionError("This event cannot allocate the trusted CI pool")
        if self.event == "pull_request" and (
            self.head_repository != self.repository or self.base_repository != self.repository
            or not re.fullmatch(r"refs/pull/[1-9][0-9]*/merge", self.ref)
        ):
            raise RunnerSelectionError("External or incomplete pull requests cannot allocate the trusted CI pool")
        if self.event != "pull_request" and not re.fullmatch(r"refs/heads/[A-Za-z0-9_./-]+", self.ref):
            raise RunnerSelectionError("A complete branch ref is required")
        if stage not in {"validation", "publication"} or requested_pool not in {"auto", "desktop-canary", "native-canary"}:
            raise RunnerSelectionError("Unknown CI stage or requested pool")
        if stage == "publication" and (
            self.event not in {"push", "workflow_dispatch"} or self.ref != "refs/heads/main" or requested_pool != "auto"
        ):
            raise RunnerSelectionError("Publication requires an ordinary trusted main run")
        if requested_pool != "auto" and (
            stage != "validation" or self.event != "workflow_dispatch" or self.ref == "refs/heads/main"
        ):
            raise RunnerSelectionError("Explicit canaries require non-main workflow dispatch and cannot publish")


@dataclass(frozen=True)
class Selection:
    profile: RunnerProfile
    label: str
    pool: str
    reason: str
    inventory_state: str
    runner_id: int | None

    def outputs(self) -> dict[str, str]:
        return dict(profile=self.profile.id, runner_label=self.label, pool=self.pool, route_reason=self.reason,
                    inventory_state=self.inventory_state, runner_id="" if self.runner_id is None else str(self.runner_id))


def normalize_inventory(rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list):
        raise RunnerSelectionError("Runner inventory must be a list")
    result, ids, names = [], set(), set()
    for row in rows:
        if (not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] < 1
                or not isinstance(row.get("name"), str) or not row["name"]
                or row["id"] in ids or row["name"] in names or row.get("status") not in ("online", "offline")
                or type(row.get("busy")) is not bool or not isinstance(row.get("labels"), list)):
            raise RunnerSelectionError("Runner inventory identity or state is malformed or duplicated")
        labels = []
        for label in row["labels"]:
            value = label.get("name") if isinstance(label, dict) else label
            if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
                raise RunnerSelectionError("Runner inventory labels are malformed")
            labels.append(value.casefold())
        if len(labels) != len(set(labels)):
            raise RunnerSelectionError("Runner inventory labels are duplicated")
        ids.add(row["id"])
        names.add(row["name"])
        result.append(dict(row, labels=frozenset(labels)))
    return result


def select_runner(policy: RoutingPolicy, context: WorkflowContext, *, stage: str, requested_pool: str,
                  selector_runner: str, runners: list[dict] | None, unavailable_reason: str = "missing-token") -> Selection:
    context.validate(stage=stage, requested_pool=requested_pool)
    if context.repository != policy.repository:
        raise RunnerSelectionError("Workflow and configured registration repositories differ")
    policy.approve_selector(selector_runner)
    if runners is None:
        if requested_pool == "desktop-canary":
            raise RunnerSelectionError("Desktop canary needs a complete available runner inventory")
        # GITHUB_TOKEN is not assumed to have runner administration-read access.
        if unavailable_reason not in {"missing-token", "redirect-refused", "timeout", "response-too-large",
                                      "request-or-json-failed", "invalid-response", "inconsistent-pagination",
                                      "invalid-records", "incomplete-pagination", "pagination-limit"} and not re.fullmatch(
                                          r"http-[1-5][0-9]{2}", unavailable_reason):
            raise RunnerSelectionError("Inventory failure reason is not a recognized safe diagnostic")
        reason = "explicit-native-canary" if requested_pool == "native-canary" else "native-fallback:inventory-unavailable"
        return Selection(policy.native, policy.native_label, "native", reason,
                         "unavailable:" + unavailable_reason, None)
    inventory = normalize_inventory(runners)

    def matching(profile: RunnerProfile, label: str) -> dict | None:
        required = PLATFORM_LABELS | {label.casefold()}
        for row in inventory:
            if required.issubset(row["labels"]) and row["name"] != profile.runner_name:
                raise RunnerSelectionError("A scheduling label also names an unapproved runner")
        return next((row for row in inventory if row["name"] == profile.runner_name), None)

    def eligible(profile: RunnerProfile, row: dict | None, label: str) -> bool:
        required = PLATFORM_LABELS | {label.casefold()}
        return (row is not None and row["status"] == "online" and required.issubset(row["labels"])
                # Managed desktop registrations have one custom scheduling
                # label. Refuse deployment labels or simultaneous canary and
                # production access even if the requested label is present.
                and (profile.kind != "desktop" or row["labels"] == required))

    if policy.desktop is not None and requested_pool != "native-canary":
        label = policy.desktop_label(canary=requested_pool == "desktop-canary")
        desktop = matching(policy.desktop, label)
        if eligible(policy.desktop, desktop, label) and (desktop["busy"] is False or desktop["name"] == selector_runner):
            reason = "explicit-desktop-canary" if requested_pool == "desktop-canary" else (
                "desktop-selector-current" if desktop["name"] == selector_runner else "desktop-idle")
            return Selection(policy.desktop, label, "desktop", reason, "available", desktop["id"])
    if requested_pool == "desktop-canary":
        raise RunnerSelectionError("The exact desktop canary is unavailable, busy or not canary-labeled")
    native = matching(policy.native, policy.native_label)
    if eligible(policy.native, native, policy.native_label):
        reason = "explicit-native-canary" if requested_pool == "native-canary" else "native-fallback:no-idle-desktop"
        return Selection(policy.native, policy.native_label, "native", reason, "available", native["id"])
    # The plan requires retaining the configured native queue when neither
    # approved pool is online; never broaden labels to find arbitrary capacity.
    return Selection(policy.native, policy.native_label, "native", "native-queue:no-approved-online-pool", "available", None)


class NoInventoryRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise InventoryUnavailable("redirect-refused")


def unique_api_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InventoryUnavailable("invalid-response")
        result[key] = value
    return result


def open_inventory_request(request: Request, *, timeout: float):
    return build_opener(NoInventoryRedirect()).open(request, timeout=timeout)


def fetch_runner_inventory(token: str, repository: str) -> list[dict]:
    if not token:
        raise InventoryUnavailable("missing-token")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise RunnerSelectionError("Repository identity is malformed")
    owner, name = repository.split("/")
    endpoint = API_ROOT + "/repos/" + quote(owner, safe="") + "/" + quote(name, safe="") + "/actions/runners"
    rows, expected = [], None
    deadline = time.monotonic() + 30
    for page in range(1, MAX_PAGES + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise InventoryUnavailable("timeout")
        request = Request(endpoint + "?" + urlencode(dict(per_page=PAGE_SIZE, page=page)), headers={
            "Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
            "User-Agent": "CI-profile-runner-selector", "X-GitHub-Api-Version": API_VERSION,
        })
        try:
            with open_inventory_request(request, timeout=min(15, remaining)) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise InventoryUnavailable("response-too-large")
            payload = json.loads(raw, object_pairs_hook=unique_api_object)
        except InventoryUnavailable:
            raise
        except HTTPError as error:
            raise InventoryUnavailable(f"http-{int(error.code)}") from None
        except TimeoutError:
            raise InventoryUnavailable("timeout") from None
        except (OSError, ValueError, HTTPException):
            raise InventoryUnavailable("request-or-json-failed") from None
        if (not isinstance(payload, dict) or type(payload.get("total_count")) is not int
                or payload["total_count"] < 0 or not isinstance(payload.get("runners"), list)):
            raise InventoryUnavailable("invalid-response")
        total, batch = payload["total_count"], payload["runners"]
        if expected is None:
            expected = total
        if total != expected or len(batch) > PAGE_SIZE or len(rows) + len(batch) > total:
            raise InventoryUnavailable("inconsistent-pagination")
        rows.extend(batch)
        if len(rows) == total:
            try:
                normalize_inventory(rows)
            except RunnerSelectionError:
                raise InventoryUnavailable("invalid-records") from None
            return rows
        if len(batch) < PAGE_SIZE:
            raise InventoryUnavailable("incomplete-pagination")
    raise InventoryUnavailable("pagination-limit")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    config = parser.add_mutually_exclusive_group(required=True)
    config.add_argument("--config", type=Path)
    config.add_argument("--config-json-env")
    parser.add_argument("--native-profile", required=True)
    parser.add_argument("--native-label", required=True)
    parser.add_argument("--desktop-profile")
    parser.add_argument("--stage", choices=("validation", "publication"), required=True)
    parser.add_argument("--pool", choices=("auto", "desktop-canary", "native-canary"), default="auto")
    arguments = parser.parse_args()
    try:
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        if not isinstance(event, dict) or event.get("repository", {}).get("full_name") != repository:
            raise RunnerSelectionError("Workflow payload does not identify this repository")
        pull = event.get("pull_request", {})
        if not isinstance(pull, dict):
            raise RunnerSelectionError("Pull request payload is malformed")
        context = WorkflowContext(repository, os.environ.get("GITHUB_EVENT_NAME", ""), os.environ.get("GITHUB_REF", ""),
                                  pull.get("head", {}).get("repo", {}).get("full_name"),
                                  pull.get("base", {}).get("repo", {}).get("full_name"))
        context.validate(stage=arguments.stage, requested_pool=arguments.pool)
        configured = load_profiles(config_path=arguments.config, config_json_env=arguments.config_json_env)
        policy = RoutingPolicy(repository, select_profile(configured, arguments.native_profile), arguments.native_label,
                               select_profile(configured, arguments.desktop_profile) if arguments.desktop_profile else None)
        if len([p for p in configured.values() if p.kind == "desktop" and p.repository == repository]) > 1:
            raise RunnerSelectionError("This repository may use only one existing desktop slot")
        selector = os.environ.get("RUNNER_NAME", "")
        policy.approve_selector(selector)
        output_path = os.environ.get("GITHUB_OUTPUT", "")
        if not output_path:
            raise RunnerSelectionError("GITHUB_OUTPUT is required")
        token = os.environ.get("CI_RUNNER_INVENTORY_TOKEN", "")
        reason, inventory = "missing-token", None
        if token:
            try:
                inventory = fetch_runner_inventory(token, repository)
            except InventoryUnavailable as error:
                reason = str(error)
        selected = select_runner(policy, context, stage=arguments.stage, requested_pool=arguments.pool,
                                 selector_runner=selector, runners=inventory, unavailable_reason=reason)
        outputs = selected.outputs()
        with open(output_path, "a", encoding="utf-8") as output:
            output.write("".join(f"{key}={value}\n" for key, value in outputs.items()))
        print(json.dumps(outputs, sort_keys=True))
        return 0
    except (RunnerSelectionError, ProfileError, OSError, ValueError, KeyError, TypeError, AttributeError):
        # Transport diagnostics and malformed payloads must never expose tokens.
        print("CI runner selection failed; no routing output was accepted.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
