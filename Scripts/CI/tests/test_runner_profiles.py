from __future__ import annotations

import copy
import json
import unittest

from Scripts.CI.runner_profiles import ProfileError, parse_profile, parse_profiles, select_profile, verify_runtime


def profile(instance: str = "secondary", repository: str = "Example/Product", kind: str = "desktop") -> dict:
    root = f"/opt/fixture-ci/{instance}"
    paths = [root + "/_work", "/opt/fixture-ci/docker", root + "/reports", root + "/tmp"]
    name = "fixture-ci-" + instance
    value = {
        "id": instance, "kind": kind,
        "repository": repository, "runnerName": name, "expectedHost": "fixture-ci",
        "labels": ["fixture-ci-desktop", "fixture-ci-canary"] if kind == "desktop" else ["fixture-ci-native"],
        "runnerRoot": root, "workspaceRoot": paths[0],
        "dockerEndpoint": "unix:///run/fixture-ci/docker.sock", "dockerId": "fixture-engine-id",
        "dockerDataRoot": paths[1], "reportRoot": paths[2], "temporaryRoot": paths[3],
        "capacityRoots": [dict(path=path, minimumFreeBytes=1024, minimumFreePercent=25,
                               minimumFreeInodePercent=5) for path in paths],
    }
    if kind == "desktop":
        value.update(instance=instance, ownerRepository="Example/Infrastructure", ownerTaskId="FIXTURE-CI",
                     markerPath=f"/etc/fixture-ci/{instance}.json",
                     service=f"actions.runner.{repository.replace('/', '-')}.{name}.service")
    return value


def document(*profiles: dict) -> str:
    return json.dumps({"schemaVersion": 1, "profiles": profiles})


class RunnerProfileTests(unittest.TestCase):
    def test_different_repositories_can_use_independent_desktop_installations(self) -> None:
        first_profile = profile("primary", "Example/Infrastructure")
        second_profile = profile("secondary", "Example/Product")
        second_profile.update(dockerEndpoint="unix:///run/other/docker.sock", dockerId="other-engine",
                              dockerDataRoot="/opt/other/docker")
        second_profile["capacityRoots"][1]["path"] = second_profile["dockerDataRoot"]
        profiles = parse_profiles(document(first_profile, second_profile))
        first = select_profile(profiles, "primary")
        second = select_profile(profiles, "secondary")
        self.assertEqual("Example/Infrastructure", second.owner_repository)
        self.assertEqual("Example/Product", second.repository)
        self.assertNotEqual(first.docker_endpoint, second.docker_endpoint)
        self.assertNotEqual(first.service, second.service)

    def test_native_profile_has_no_desktop_installation_contract(self) -> None:
        profiles = parse_profiles(document(profile("native", "Example/Product", "native")))
        selected = select_profile(profiles, "native")
        self.assertEqual("native", selected.kind)
        self.assertIsNone(selected.marker_path)
        self.assertIsNone(selected.service)
        self.assertIsNone(selected.owner_repository)

    def test_unknown_or_missing_selected_profile_is_rejected(self) -> None:
        profiles = parse_profiles(document(profile()))
        for selected in (None, "", "unconfigured"):
            with self.subTest(selected=selected), self.assertRaises(ProfileError):
                select_profile(profiles, selected)

    def test_missing_fields_empty_identities_unknown_kind_and_deployment_labels_are_rejected(self) -> None:
        invalid = [dict(profile(), kind="other"), dict(profile(), kind=[]), dict(profile(), labels=[]),
                   dict(profile(), labels=["localcluster-product"]),
                   dict(profile(), labels=["ci-deploy-product"]),
                   dict(profile(), labels=["fixture-ci-desktop", "fixture-ci-canary", "fixture-ci-extra"]),
                   dict(profile(), labels=["fixture-ci-desktop", "fixture-ci-preview"]),
                   dict(profile(), labels=["self-hosted"]),
                   dict(profile(), labels=["fixture-ci", "FIXTURE-CI"])]
        for field in ("repository", "expectedHost", "dockerId", "runnerName"):
            invalid.append(dict(profile(), **{field: ""}))
        for field in ("ownerRepository", "ownerTaskId", "instance"):
            invalid.append(dict(profile(), **{field: ""}))
        missing = profile()
        del missing["markerPath"]
        invalid.extend([missing, dict(profile(), unknown=True)])
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ProfileError):
                parse_profile(value)
        with self.assertRaises(ProfileError):
            parse_profile(dict(profile(kind="native"), markerPath="/etc/fixture-ci/native.json"))

    def test_service_cannot_name_an_unrelated_system_service_or_inject_arguments(self) -> None:
        for service in ("docker.service", "../actions.runner.other.service", "actions.runner.other.service --now"):
            with self.subTest(service=service), self.assertRaises(ProfileError):
                parse_profile(dict(profile(), service=service))

    def test_windows_paths_traversal_and_external_docker_endpoints_are_rejected(self) -> None:
        for path in ("/mnt/c/worker", "C:\\worker", "relative", "/opt/../worker", "/opt//worker", "/"):
            with self.subTest(path=path), self.assertRaises(ProfileError):
                parse_profile(dict(profile(), runnerRoot=path))
        with self.assertRaises(ProfileError):
            parse_profile(dict(profile(), dockerEndpoint="tcp://unapproved:2375"))

    def test_capacity_cannot_check_an_ancestor_instead_of_each_real_root(self) -> None:
        value = profile()
        value["capacityRoots"][0]["path"] = "/opt"
        with self.assertRaisesRegex(ProfileError, "cover each actual"):
            parse_profile(value)
        for threshold in (0, -1, True, "1024"):
            value = profile()
            value["capacityRoots"][0]["minimumFreeBytes"] = threshold
            with self.subTest(threshold=threshold), self.assertRaises(ProfileError):
                parse_profile(value)

    def test_a_repository_cannot_configure_two_desktop_profiles(self) -> None:
        with self.assertRaisesRegex(ProfileError, "one desktop profile"):
            parse_profiles(document(profile("primary"), profile("secondary")))

    def test_engine_roots_are_profile_specific_and_nested_installations_are_rejected(self) -> None:
        first, second = profile("primary"), profile()
        second["repository"] = "Other/Product"
        second["service"] = "actions.runner.Other-Product.fixture-ci-secondary.service"
        second["dockerDataRoot"] = "/opt/other/docker"
        second["capacityRoots"][1]["path"] = second["dockerDataRoot"]
        parse_profile(second)
        profiles = parse_profiles(document(first, second))
        self.assertNotEqual(profiles["primary"].docker_data_root, profiles["secondary"].docker_data_root)
        second = profile("secondary", "Other/Product")
        second["service"] = "actions.runner.Other-Product.fixture-ci-secondary.service"
        second["runnerRoot"] = first["runnerRoot"] + "/nested"
        second["workspaceRoot"] = second["runnerRoot"] + "/_work"
        second["capacityRoots"][0]["path"] = second["workspaceRoot"]
        parse_profile(second)
        with self.assertRaisesRegex(ProfileError, "must not overlap"):
            parse_profiles(document(first, second))

    def test_malformed_and_ambiguous_json_fails_closed(self) -> None:
        for text in ("{", '[]', '{"schemaVersion":1,"schemaVersion":1,"profiles":[]}',
                     '{"schemaVersion":true,"profiles":[]}', '{"schemaVersion":2,"profiles":[]}'):
            with self.subTest(text=text), self.assertRaises(ProfileError):
                parse_profiles(text)

    def test_runtime_requires_exact_host_runner_repository_workspace_and_daemon(self) -> None:
        configured = parse_profile(profile())
        observed = dict(repository=configured.repository, runner_name=configured.runner_name,
                        runner_os="Linux", hostname=configured.expected_host,
                        workspace=str(configured.workspace_root / "Product/Product"),
                        docker_endpoint=configured.docker_endpoint,
                        docker_info={"ID": configured.docker_id, "DockerRootDir": str(configured.docker_data_root), "OSType": "linux"})
        verify_runtime(configured, **observed)
        invalid = [dict(observed, **{field: "wrong"}) for field in
                   ("repository", "runner_name", "runner_os", "hostname", "docker_endpoint")]
        invalid.extend(dict(observed, workspace=value) for value in ("/mnt/c/worker", "/opt/another/_work"))
        for field in ("ID", "DockerRootDir", "OSType"):
            modified = copy.deepcopy(observed)
            modified["docker_info"][field] = "wrong"
            invalid.append(modified)
        for observation in invalid:
            with self.subTest(observation=observation), self.assertRaises(ProfileError):
                verify_runtime(configured, **observation)


if __name__ == "__main__":
    unittest.main()
