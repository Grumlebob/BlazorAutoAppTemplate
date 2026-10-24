from __future__ import annotations

import copy
import contextlib
from dataclasses import replace
from http.client import HTTPException, IncompleteRead
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from Scripts.CI import select_ci_runner as selector
from Scripts.CI.runner_profiles import parse_profile
from Scripts.CI.tests.test_runner_profiles import profile, document


REPOSITORY = "Example/Product"
DESKTOP = profile()
NATIVE = dict(profile("native", kind="native"), labels=["fixture-ci-native"])


def policy(*, desktop=True):
    return selector.RoutingPolicy(REPOSITORY, parse_profile(NATIVE), "fixture-ci-native",
                                  parse_profile(DESKTOP) if desktop else None)


def runner(native=False, **changes):
    value = NATIVE if native else DESKTOP
    label = value["labels"][0]
    return dict(id=21 if native else 123, name=value["runnerName"], status="online", busy=False,
                labels=["self-hosted", "Linux", "X64", label]) | changes


def context(event="pull_request", ref="refs/pull/7/merge"):
    return selector.WorkflowContext(REPOSITORY, event, ref, REPOSITORY, REPOSITORY)


class RoutingTests(unittest.TestCase):
    def select(self, rows=None, **changes):
        arguments = dict(stage="validation", requested_pool="auto", selector_runner=NATIVE["runnerName"],
                         runners=[runner(), runner(True)] if rows is None else rows)
        arguments.update(changes)
        return selector.select_runner(policy(), context(), **arguments)

    def test_prefers_only_the_approved_idle_desktop(self):
        result = self.select()
        self.assertEqual(("secondary", "fixture-ci-desktop", 123, "desktop-idle"),
                         (result.profile.id, result.label, result.runner_id, result.reason))

    def test_busy_offline_drained_missing_or_wrong_platform_desktop_uses_native(self):
        cases = [runner(busy=True), runner(status="offline"), runner(labels=["self-hosted", "Linux", "X64"]),
                 runner(labels=["self-hosted", "Windows", "X64", "fixture-ci-desktop"]), None]
        for desktop in cases:
            with self.subTest(desktop=desktop):
                rows = ([desktop] if desktop else []) + [runner(True, busy=True)]
                result = self.select(rows)
                self.assertEqual(("native", 21), (result.pool, result.runner_id))

    def test_current_desktop_selector_is_expected_to_be_busy(self):
        result = self.select([runner(busy=True), runner(True)], selector_runner=DESKTOP["runnerName"])
        self.assertEqual("desktop-selector-current", result.reason)

    def test_extra_desktop_labels_cannot_allocate_normal_or_canary_jobs(self):
        for extra in ("localcluster-product", "unapproved-ci", "fixture-ci-canary"):
            with self.subTest(extra=extra):
                desktop = runner()
                desktop["labels"].append(extra)
                self.assertEqual("native", self.select([desktop, runner(True)]).pool)
                # Being the selector never excuses an unsafe desktop label.
                self.assertEqual("native", self.select([desktop, runner(True)],
                                                       selector_runner=DESKTOP["runnerName"]).pool)
        for extra in ("localcluster-product", "unapproved-ci", "fixture-ci-desktop"):
            with self.subTest(canary_extra=extra), self.assertRaises(selector.RunnerSelectionError):
                selector.select_runner(policy(), context("workflow_dispatch", "refs/heads/owned-canary"),
                                       stage="validation", requested_pool="desktop-canary",
                                       selector_runner=NATIVE["runnerName"], runners=[runner(labels=[
                                           "self-hosted", "Linux", "X64", "fixture-ci-canary", extra]), runner(True)])

    def test_existing_native_deployment_labels_do_not_block_native_ci(self):
        native = runner(True)
        native["labels"].append("localcluster-product")
        result = self.select([runner(status="offline"), native])
        self.assertEqual(("native", 21), (result.pool, result.runner_id))

    def test_unavailable_inventory_keeps_configured_native_and_distinguishes_the_reason(self):
        for reason in ("missing-token", "http-403", "timeout", "incomplete-pagination"):
            with self.subTest(reason=reason):
                result = self.select(runners=None, unavailable_reason=reason)
                self.assertEqual(("native", "fixture-ci-native", "unavailable:" + reason, None),
                                 (result.pool, result.label, result.inventory_state, result.runner_id))

    def test_neither_pool_online_queues_only_configured_native(self):
        for rows in ([], [runner(status="offline")], [runner(status="offline"), runner(True, status="offline")]):
            with self.subTest(rows=rows):
                result = self.select(rows)
                self.assertEqual(("fixture-ci-native", "native-queue:no-approved-online-pool", None),
                                 (result.label, result.reason, result.runner_id))

    def test_native_only_clone_works_without_a_desktop_registration(self):
        result = selector.select_runner(policy(desktop=False), context(), stage="validation", requested_pool="auto",
                                        selector_runner=NATIVE["runnerName"], runners=[runner(True)])
        self.assertEqual("native", result.pool)

    def test_publication_reevaluates_a_new_snapshot_instead_of_validation_choice(self):
        validation = self.select()
        publication = selector.select_runner(policy(), context("push", "refs/heads/main"),
                                              stage="publication", requested_pool="auto",
                                              selector_runner=NATIVE["runnerName"],
                                              runners=[runner(status="offline"), runner(True)])
        self.assertEqual(("desktop", "native"), (validation.pool, publication.pool))
        # A later publication may also use the desktop after native validation.
        validation = self.select([runner(busy=True), runner(True)])
        publication = selector.select_runner(policy(), context("push", "refs/heads/main"),
                                              stage="publication", requested_pool="auto",
                                              selector_runner=NATIVE["runnerName"], runners=[runner(), runner(True)])
        self.assertEqual(("native", "desktop"), (validation.pool, publication.pool))

    def test_unknown_selector_and_unapproved_runner_with_the_route_label_are_rejected(self):
        for name in ("", None, "unapproved"):
            with self.subTest(name=name), self.assertRaises(selector.RunnerSelectionError):
                self.select(selector_runner=name)
        for native in (True, False):
            rows = [runner(name="unapproved")] if not native else [runner(status="offline"), runner(True, name="unapproved")]
            with self.subTest(native=native), self.assertRaises(selector.RunnerSelectionError):
                self.select(rows)

    def test_canary_requires_available_exact_canary_and_never_silently_falls_back(self):
        canary_context = context("workflow_dispatch", "refs/heads/owned-canary")
        arguments = dict(stage="validation", requested_pool="desktop-canary", selector_runner=NATIVE["runnerName"])
        result = selector.select_runner(policy(), canary_context, runners=[
            runner(labels=["self-hosted", "Linux", "X64", "fixture-ci-canary"]), runner(True)], **arguments)
        self.assertEqual(("desktop", "explicit-desktop-canary", "fixture-ci-canary"),
                         (result.pool, result.reason, result.label))
        for rows in (None, [], [runner()], [runner(busy=True, labels=["self-hosted", "Linux", "X64", "fixture-ci-canary"])]):
            with self.subTest(rows=rows), self.assertRaises(selector.RunnerSelectionError):
                selector.select_runner(policy(), canary_context, runners=rows, **arguments)

    def test_forks_main_canaries_and_non_main_publication_cannot_allocate(self):
        invalid = [
            (replace(context(), head_repository="External/Fork"), "validation", "auto"),
            (replace(context(), base_repository=None), "validation", "auto"),
            (replace(context(), ref=""), "validation", "auto"),
            (context("pull_request_target", "refs/heads/main"), "validation", "auto"),
            (context("workflow_dispatch", "refs/heads/main"), "validation", "desktop-canary"),
            (context("push", "refs/heads/feature"), "publication", "auto"),
            (context("workflow_dispatch", "refs/heads/feature"), "publication", "desktop-canary"),
        ]
        for run, stage, pool in invalid:
            with self.subTest(run=run, stage=stage, pool=pool), self.assertRaises(selector.RunnerSelectionError):
                selector.select_runner(policy(), run, stage=stage, requested_pool=pool,
                                        selector_runner=NATIVE["runnerName"], runners=None)

    def test_policy_and_observed_inventory_refuse_ambiguous_or_malformed_identities(self):
        for changes in (dict(repository="External/Repo"), dict(native_label="localcluster"),
                        dict(desktop=parse_profile(dict(DESKTOP, repository="External/Repo")))):
            with self.subTest(changes=changes), self.assertRaises(selector.RunnerSelectionError):
                replace(policy(), **changes)
        for rows in ([runner(id=True)], [runner(), runner()], [runner(busy=None)], [runner(status=[])],
                     [runner(labels=["Linux", "linux"])], [runner(labels=[{"name": None}])]):
            with self.subTest(rows=rows), self.assertRaises(selector.RunnerSelectionError):
                self.select(rows)


class InventoryTests(unittest.TestCase):
    def test_all_pages_are_repository_scoped_complete_and_authenticated_with_the_explicit_token(self):
        rows = [runner(True, id=index + 1, name=f"fixture-{index}") for index in range(selector.PAGE_SIZE)]
        payloads = [BytesIO(json.dumps(dict(total_count=101, runners=rows)).encode()),
                    BytesIO(json.dumps(dict(total_count=101, runners=[runner()])).encode())]
        requests = []
        def opened(request, *, timeout):
            requests.append((request, timeout))
            return payloads.pop(0)
        with patch.object(selector, "open_inventory_request", side_effect=opened):
            result = selector.fetch_runner_inventory("fixture-read-token", REPOSITORY)
        self.assertEqual(101, len(result))
        self.assertEqual(2, len(requests))
        self.assertEqual("https://api.github.com/repos/Example/Product/actions/runners?per_page=100&page=2",
                         requests[1][0].full_url)
        self.assertEqual("Bearer fixture-read-token", requests[0][0].get_header("Authorization"))
        self.assertEqual(selector.API_VERSION, requests[0][0].get_header("X-github-api-version"))
        self.assertLessEqual(requests[0][1], 15)

    def test_denied_timeout_or_malformed_response_has_only_a_safe_failure_reason(self):
        secret = "fixture-token-never-print"
        for failure in (HTTPError("https://api.github.com/" + secret, 403, secret, {}, None), TimeoutError(secret),
                        OSError(secret), HTTPException(secret)):
            with self.subTest(failure=type(failure).__name__), patch.object(
                    selector, "open_inventory_request", side_effect=failure):
                with self.assertRaises(selector.InventoryUnavailable) as observed:
                    selector.fetch_runner_inventory(secret, REPOSITORY)
                self.assertNotIn(secret, str(observed.exception))
        bad = [b"{", b'{"total_count":true,"runners":[]}', b'{"total_count":0,"total_count":1,"runners":[]}',
               json.dumps(dict(total_count=2, runners=[runner()])).encode(),
               json.dumps(dict(total_count=1, runners=[runner(id=True)])).encode()]
        for payload in bad:
            with self.subTest(payload=payload), patch.object(selector, "open_inventory_request", return_value=BytesIO(payload)):
                with self.assertRaises(selector.InventoryUnavailable):
                    selector.fetch_runner_inventory(secret, REPOSITORY)

    def test_pagination_change_and_redirect_never_produce_a_partial_approved_snapshot(self):
        first = [runner(True, id=index + 1, name=f"row-{index}") for index in range(selector.PAGE_SIZE)]
        pages = [BytesIO(json.dumps(dict(total_count=101, runners=first)).encode()),
                 BytesIO(json.dumps(dict(total_count=102, runners=[runner()])).encode())]
        with patch.object(selector, "open_inventory_request", side_effect=pages):
            with self.assertRaisesRegex(selector.InventoryUnavailable, "inconsistent-pagination"):
                selector.fetch_runner_inventory("fixture-read-token", REPOSITORY)
        with self.assertRaisesRegex(selector.InventoryUnavailable, "redirect-refused"):
            selector.NoInventoryRedirect().redirect_request(None, None, 302, "", {}, "https://unapproved.example")


class SelectorCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.config, self.event, self.output = root / "profiles.json", root / "event.json", root / "output"
        self.config.write_text(document(NATIVE, DESKTOP))
        self.payload = dict(repository=dict(full_name=REPOSITORY), pull_request=dict(
            head=dict(repo=dict(full_name=REPOSITORY)), base=dict(repo=dict(full_name=REPOSITORY))))
        self.event.write_text(json.dumps(self.payload))
        self.environment = dict(GITHUB_REPOSITORY=REPOSITORY, GITHUB_EVENT_PATH=str(self.event),
                                GITHUB_EVENT_NAME="pull_request", GITHUB_REF="refs/pull/7/merge",
                                RUNNER_NAME=NATIVE["runnerName"], GITHUB_OUTPUT=str(self.output))
        self.arguments = ["select_ci_runner.py", "--config", str(self.config), "--native-profile", "native",
                          "--native-label", "fixture-ci-native", "--desktop-profile", "secondary", "--stage", "validation"]

    def invoke(self, changes=None, *, inventory=None, failure=None, arguments=None):
        stdout, stderr = StringIO(), StringIO()
        with (patch.dict(os.environ, self.environment | (changes or {}), clear=True),
              patch.object(selector.sys, "argv", self.arguments if arguments is None else arguments),
              patch.object(selector, "fetch_runner_inventory", return_value=inventory, side_effect=failure) as fetch,
              contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr)):
            result = selector.main()
        return result, stdout.getvalue(), stderr.getvalue(), fetch

    def test_github_token_alone_does_not_claim_runner_inventory_permission(self):
        result, stdout, _, fetch = self.invoke(dict(GITHUB_TOKEN="fixture-ordinary-token"))
        self.assertEqual(0, result)
        fetch.assert_not_called()
        outputs = dict(line.split("=", 1) for line in self.output.read_text().splitlines())
        self.assertEqual(("native", "fixture-ci-native", "unavailable:missing-token"),
                         (outputs["profile"], outputs["runner_label"], outputs["inventory_state"]))
        self.assertNotIn("fixture-ordinary-token", stdout)

    def test_cli_emits_profile_label_and_observed_registration_id_from_the_fresh_snapshot(self):
        result, stdout, stderr, fetch = self.invoke(dict(CI_RUNNER_INVENTORY_TOKEN="fixture-read-token"),
                                                  inventory=[runner(), runner(True)])
        self.assertEqual(0, result, stderr)
        fetch.assert_called_once_with("fixture-read-token", REPOSITORY)
        outputs = json.loads(stdout)
        self.assertEqual(("secondary", "fixture-ci-desktop", "123"), (outputs["profile"], outputs["runner_label"], outputs["runner_id"]))
        self.assertNotIn("fixture-read-token", self.output.read_text())

    def test_cli_inventory_failure_falls_back_without_logging_credentials(self):
        result, stdout, stderr, _ = self.invoke(dict(CI_RUNNER_INVENTORY_TOKEN="fixture-read-token"),
                                               failure=selector.InventoryUnavailable("http-403"))
        self.assertEqual(0, result, stderr)
        self.assertEqual("unavailable:http-403", json.loads(stdout)["inventory_state"])
        self.assertNotIn("fixture-read-token", stdout + stderr + self.output.read_text())

    def test_cli_reads_private_profiles_from_an_environment_value_without_echoing_them(self):
        private_host = "private-runner.example"
        private_document = json.loads(document(NATIVE, DESKTOP))
        private_document["profiles"][0]["expectedHost"] = private_host
        secret = json.dumps(private_document)
        arguments = ["select_ci_runner.py", "--config-json-env", "CI_RUNNER_PROFILES_JSON",
                     "--native-profile", "native", "--native-label", "fixture-ci-native",
                     "--desktop-profile", "secondary", "--stage", "validation"]
        result, stdout, stderr, fetch = self.invoke(
            {"CI_RUNNER_PROFILES_JSON": secret}, arguments=arguments,
        )
        self.assertEqual(0, result, stderr)
        fetch.assert_not_called()
        self.assertEqual("native", json.loads(stdout)["profile"])
        self.assertNotIn(private_host, stdout + stderr + self.output.read_text())

    def test_cli_missing_profile_environment_fails_without_emitting_routing(self):
        arguments = ["select_ci_runner.py", "--config-json-env", "CI_RUNNER_PROFILES_JSON",
                     "--native-profile", "native", "--native-label", "fixture-ci-native",
                     "--desktop-profile", "secondary", "--stage", "validation"]
        result, stdout, stderr, fetch = self.invoke(arguments=arguments)
        self.assertEqual(1, result)
        self.assertEqual("", stdout)
        self.assertIn("CI runner selection failed", stderr)
        fetch.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_cli_truncated_http_body_uses_native_without_logging_partial_bytes_or_credentials(self):
        secret = "fixture-read-token"
        response = BytesIO()
        with (patch.object(selector, "open_inventory_request", return_value=response),
              patch.object(response, "read", side_effect=IncompleteRead(secret.encode(), 100))):
            result, stdout, stderr, fetch = self.invoke(dict(CI_RUNNER_INVENTORY_TOKEN=secret),
                                                       failure=selector.fetch_runner_inventory)
        self.assertEqual(0, result, stderr)
        fetch.assert_called_once_with(secret, REPOSITORY)
        outputs = json.loads(stdout)
        self.assertEqual(("native", "fixture-ci-native", "unavailable:request-or-json-failed"),
                         (outputs["profile"], outputs["runner_label"], outputs["inventory_state"]))
        self.assertNotIn(secret, stdout + stderr + self.output.read_text())

    def test_fork_unknown_selector_and_malformed_payload_do_not_fetch_or_emit_routing(self):
        cases = [({}, dict(self.payload, pull_request=dict(head=dict(repo=dict(full_name="External/Fork")), base=self.payload["pull_request"]["base"]))),
                 (dict(RUNNER_NAME="unapproved"), self.payload),
                 ({}, dict(self.payload, pull_request=dict(head=None)))]
        for changes, payload in cases:
            with self.subTest(changes=changes, payload=payload):
                self.event.write_text(json.dumps(payload))
                self.output.write_text("existing=true\n")
                result, _, _, fetch = self.invoke(changes | dict(CI_RUNNER_INVENTORY_TOKEN="fixture-read-token"))
                self.assertEqual(1, result)
                fetch.assert_not_called()
                self.assertEqual("existing=true\n", self.output.read_text())


if __name__ == "__main__":
    unittest.main()
