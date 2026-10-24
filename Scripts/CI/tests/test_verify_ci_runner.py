from __future__ import annotations

from dataclasses import replace
import contextlib
import io
import json
import os
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from Scripts.CI.runner_profiles import ProfileError, parse_profile
from Scripts.CI import verify_ci_runner as runtime
from Scripts.CI.tests.test_runner_profiles import profile


@unittest.skipUnless(os.name == "posix", "requires actual Linux filesystems and mount metadata")
class RuntimeFilesystemTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        value = profile()
        value["runnerRoot"] = str(self.root / "runner")
        for field, relative in (("workspaceRoot", "runner/_work"), ("reportRoot", "runner/reports"),
                                ("temporaryRoot", "runner/_work/_temp"), ("dockerDataRoot", "docker")):
            value[field] = str(self.root / relative)
            Path(value[field]).mkdir(parents=True, exist_ok=True)
        value["markerPath"] = str(self.root / "runner-marker.json")
        value["capacityRoots"] = [dict(path=value[field], minimumFreeBytes=1, minimumFreePercent=1,
                                      minimumFreeInodePercent=1)
                                  for field in ("workspaceRoot", "reportRoot", "temporaryRoot", "dockerDataRoot")]
        self.profile = parse_profile(value)
        self.raw_profile = value

    def test_every_real_path_is_checked_and_identical_filesystems_are_combined(self):
        inspected = []
        real_statvfs = os.statvfs

        def observe(path):
            inspected.append(str(path))
            return real_statvfs(path)

        with patch.object(runtime.os, "statvfs", side_effect=observe):
            result = runtime.inspect_capacity(self.profile)
        expected = [str(root.path) for root in self.profile.capacity_roots]
        self.assertEqual(expected, inspected)
        self.assertEqual(1, len(result["filesystems"]))
        self.assertEqual(set(expected), {item["path"] for item in result["filesystems"][0]["paths"]})

    def test_combined_filesystem_report_retains_conservative_per_path_observations(self):
        observations = [SimpleNamespace(f_blocks=1000, f_frsize=4096, f_files=1000,
                                        f_bavail=available, f_favail=inodes)
                        for available, inodes in ((500, 450), (400, 350), (300, 250), (200, 150))]
        with patch.object(runtime.os, "statvfs", side_effect=observations):
            result = runtime.inspect_capacity(self.profile)
        grouped = result["filesystems"][0]
        self.assertEqual(1, len(result["filesystems"]))
        self.assertEqual((200 * 4096, 20, 15),
                         (grouped["availableBytes"], grouped["freePercent"], grouped["freeInodePercent"]))
        self.assertEqual([item.f_bavail * 4096 for item in observations],
                         [item["availableBytes"] for item in grouped["paths"]])

    def test_missing_root_and_symlinked_parent_never_use_ancestor_capacity(self):
        missing = replace(self.profile.capacity_roots[0], path=PurePosixPath(str(self.root / "missing/_work")))
        with self.assertRaises(ProfileError):
            runtime.inspect_capacity(replace(self.profile, capacity_roots=(missing,)))
        linked = self.root / "linked"
        linked.symlink_to(Path(str(self.profile.runner_root)), target_is_directory=True)
        with self.assertRaises(ProfileError):
            runtime.canonical_directory(linked / "_work")

    def test_byte_and_inode_reserves_are_enforced_for_each_path(self):
        healthy = dict(f_blocks=1000, f_frsize=4096, f_files=1000, f_bavail=500, f_favail=500)
        for changes in (dict(f_bavail=0), dict(f_favail=0), dict(f_files=0), dict(f_blocks=0)):
            with self.subTest(changes=changes), patch.object(runtime.os, "statvfs", return_value=SimpleNamespace(**(healthy | changes))):
                with self.assertRaises(ProfileError):
                    runtime.inspect_capacity(self.profile)
        high = replace(self.profile.capacity_roots[-1], minimum_free_bytes=10**18)
        with self.assertRaisesRegex(ProfileError, "reserve"):
            runtime.inspect_capacity(replace(self.profile, capacity_roots=(*self.profile.capacity_roots[:-1], high)))

    def test_percentage_reserves_are_independent_and_accept_exact_thresholds(self):
        roots = tuple(replace(root, minimum_free_bytes=1, minimum_free_percent=5,
                              minimum_free_inode_percent=5) for root in self.profile.capacity_roots)
        selected = replace(self.profile, capacity_roots=roots)
        boundary = dict(f_blocks=1000, f_frsize=4096, f_files=1000, f_bavail=50, f_favail=50)
        with patch.object(runtime.os, "statvfs", return_value=SimpleNamespace(**boundary)):
            runtime.inspect_capacity(selected)
        for changes in (dict(f_bavail=49), dict(f_favail=49)):
            with self.subTest(changes=changes), patch.object(
                    runtime.os, "statvfs", return_value=SimpleNamespace(**(boundary | changes))):
                with self.assertRaisesRegex(ProfileError, "reserve"):
                    runtime.inspect_capacity(selected)

    def test_windows_mount_type_is_rejected_even_at_a_linux_looking_path(self):
        directory = Path(str(self.profile.workspace_root))
        device = directory.stat().st_dev
        metadata = self.root / "mountinfo"
        identity = f"{os.major(device)}:{os.minor(device)}"
        metadata.write_text(f"10 1 {identity} / / rw - 9p C: rw\n")
        with self.assertRaisesRegex(ProfileError, "Linux filesystem"):
            runtime.mount_for(directory, metadata)
        metadata.write_text("broken mount record\n")
        with self.assertRaisesRegex(ProfileError, "malformed"):
            runtime.mount_for(directory, metadata)

    def test_native_registration_needs_no_desktop_owner_marker(self):
        raw = profile(instance="native", kind="native")
        runner_root = self.root / "native-runner"
        workspace = runner_root / "_work"
        workspace.mkdir(parents=True)
        raw["runnerRoot"] = str(runner_root)
        raw["workspaceRoot"] = str(workspace)
        raw["capacityRoots"][0]["path"] = str(workspace)
        selected = parse_profile(raw)
        (runner_root / ".runner").write_text(json.dumps(dict(
            agentId=123, agentName=selected.runner_name,
            gitHubUrl="https://github.com/" + selected.repository, workFolder="_work",
        )))
        self.assertIsNone(selected.marker_path)
        self.assertEqual(123, runtime.verify_local_registration(
            selected, selected_label=selected.labels[0], expected_runner_id=123,
        ))

    def test_registration_and_owner_marker_must_both_match_the_selected_slot(self):
        registration = dict(agentId=123, agentName=self.profile.runner_name,
                            gitHubUrl="https://github.com/" + self.profile.repository, workFolder="_work")
        marker = dict(repository=self.profile.repository, taskId=self.profile.owner_task_id,
                      ownerRepository=self.profile.owner_repository, ownerTaskId=self.profile.owner_task_id,
                      runnerRoot=str(self.profile.runner_root), runnerName=self.profile.runner_name, runnerId=123,
                      serviceName=self.profile.service, state="service-installed", customLabels=[self.profile.labels[0]])
        registration_path = Path(str(self.profile.runner_root)) / ".runner"
        marker_path = Path(str(self.profile.marker_path))
        real_stat = Path.stat

        def root_owned(path, *args, **kwargs):
            info = real_stat(path, *args, **kwargs)
            return SimpleNamespace(st_mode=info.st_mode, st_uid=0, st_gid=0) if path == marker_path else info

        registration_path.write_text(json.dumps(registration), encoding="utf-8-sig")
        marker_path.write_text(json.dumps(marker))
        marker_path.chmod(0o644)
        with patch.object(Path, "stat", root_owned):
            self.assertEqual(123, runtime.verify_local_registration(self.profile, expected_runner_id=123))
            for wrong_id in (999, True, 0, -1, "123"):
                with self.subTest(wrong_id=wrong_id), self.assertRaisesRegex(ProfileError, "registration ID"):
                    runtime.verify_local_registration(self.profile, expected_runner_id=wrong_id)
            with self.assertRaisesRegex(ProfileError, "Selected scheduling label"):
                runtime.verify_local_registration(self.profile, selected_label=self.profile.labels[1])
            for wrong in (dict(marker, repository="Other/Repository"), dict(marker, ownerRepository="Other/Owner"),
                          dict(marker, runnerId=999), dict(marker, runnerId=True), dict(marker, customLabels=["ci-deploy"]),
                          dict(marker, serviceName="docker.service")):
                marker_path.write_text(json.dumps(wrong))
                with self.assertRaises(ProfileError):
                    runtime.verify_local_registration(self.profile)
            marker_path.write_text(json.dumps(marker))
            registration_path.write_text(json.dumps(dict(registration, gitHubUrl="https://github.com/Other/Repository")))
            with self.assertRaises(ProfileError):
                runtime.verify_local_registration(self.profile)

    def test_cli_reads_only_the_explicit_daemon_and_rejects_wrong_runtime_identity(self):
        config = self.root / "profiles.json"
        config.write_text(json.dumps(dict(schemaVersion=1, profiles=[self.raw_profile])))
        registration_path = Path(str(self.profile.runner_root)) / ".runner"
        registration_path.write_text(json.dumps(dict(
            agentId=123, agentName=self.profile.runner_name,
            gitHubUrl="https://github.com/" + self.profile.repository, workFolder="_work",
        )))
        marker_path = Path(str(self.profile.marker_path))
        marker_path.write_text(json.dumps(dict(
            repository=self.profile.repository, taskId=self.profile.owner_task_id,
            ownerRepository=self.profile.owner_repository, ownerTaskId=self.profile.owner_task_id,
            runnerRoot=str(self.profile.runner_root), runnerName=self.profile.runner_name, runnerId=123,
            serviceName=self.profile.service, state="service-installed", customLabels=[self.profile.labels[0]],
        )))
        marker_path.chmod(0o644)
        environment = dict(GITHUB_REPOSITORY=self.profile.repository, RUNNER_NAME=self.profile.runner_name,
                           RUNNER_OS="Linux", GITHUB_WORKSPACE=str(self.profile.workspace_root),
                           DOCKER_HOST=self.profile.docker_endpoint)
        real_stat = Path.stat

        def root_owned(path, *args, **kwargs):
            info = real_stat(path, *args, **kwargs)
            return SimpleNamespace(st_mode=info.st_mode, st_uid=0, st_gid=0) if path == marker_path else info

        information = dict(ID=self.profile.docker_id, DockerRootDir=str(self.profile.docker_data_root), OSType="linux")
        argv = ["verify_ci_runner.py", "--config", str(config), "--profile", self.profile.id,
                "--label", self.profile.labels[0]]
        cases = [(changes, information, self.profile.expected_host, 123) for changes in (
            {}, dict(RUNNER_NAME="unapproved"), dict(GITHUB_REPOSITORY="Other/Repository"),
            dict(RUNNER_OS="Windows"), dict(DOCKER_HOST="tcp://unapproved:2375"),
            dict(DOCKER_CONTEXT="unapproved"), dict(GITHUB_WORKSPACE=str(self.root)))]
        cases += [({}, information | changes, self.profile.expected_host, 123) for changes in (
            dict(ID="another-engine"), dict(DockerRootDir=str(self.root)), dict(OSType="windows"))]
        cases.append(({}, information, "another-host", 123))
        cases += [({}, information, self.profile.expected_host, value) for value in (None, 999)]
        for changes, observed_docker, observed_host, expected_runner_id in cases:
            output, errors = io.StringIO(), io.StringIO()
            with (self.subTest(changes=changes, docker=observed_docker, host=observed_host),
                  patch.dict(os.environ, environment | changes, clear=True),
                  patch.object(runtime.sys, "argv", argv + (
                      ["--runner-id", str(expected_runner_id)] if expected_runner_id is not None else [])),
                  patch.object(runtime.socket, "gethostname", return_value=observed_host),
                  patch.object(Path, "stat", root_owned),
                  patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps(observed_docker))) as docker,
                  contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors)):
                result = runtime.main()
            failure = (bool(changes) or observed_docker != information or observed_host != self.profile.expected_host
                       or expected_runner_id not in (None, 123))
            self.assertEqual(1 if failure else 0, result, errors.getvalue())
            if changes.get("DOCKER_HOST") or changes.get("DOCKER_CONTEXT") or expected_runner_id == 999:
                docker.assert_not_called()
            elif not failure:
                self.assertEqual("passed", json.loads(output.getvalue())["result"])
                self.assertEqual(123, json.loads(output.getvalue())["runnerId"])
                docker.assert_called_once_with(
                    ["docker", "--host", self.profile.docker_endpoint, "info", "--format", "{{json .}}"],
                    check=True, capture_output=True, text=True, timeout=30,
                )

        output, errors = io.StringIO(), io.StringIO()
        secret = config.read_text(encoding="utf-8")

        def docker_without_profile_secret(*args, **kwargs):
            self.assertNotIn("CI_RUNNER_PROFILES_JSON", os.environ)
            return SimpleNamespace(stdout=json.dumps(information))

        with (patch.dict(os.environ, environment | {"CI_RUNNER_PROFILES_JSON": secret}, clear=True),
              patch.object(runtime.sys, "argv", [
                  "verify_ci_runner.py", "--config-json-env", "CI_RUNNER_PROFILES_JSON",
                  "--profile", self.profile.id, "--label", self.profile.labels[0], "--runner-id", "123",
              ]),
              patch.object(runtime.socket, "gethostname", return_value=self.profile.expected_host),
              patch.object(Path, "stat", root_owned),
              patch.object(runtime.subprocess, "run", side_effect=docker_without_profile_secret) as docker,
              contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors)):
            result = runtime.main()
        self.assertEqual(0, result, errors.getvalue())
        report = json.loads(output.getvalue())
        self.assertEqual("passed", report["result"])
        self.assertEqual((123, 4), (report["runnerId"], report["rootsChecked"]))
        self.assertNotIn(str(self.root), output.getvalue())
        self.assertNotIn("runnerRoot", output.getvalue())
        self.assertNotIn("mountId", output.getvalue())
        self.assertNotIn("source", output.getvalue())
        docker.assert_called_once()

        output, errors = io.StringIO(), io.StringIO()
        with (patch.dict(os.environ, environment | {"CI_RUNNER_PROFILES_JSON": secret}, clear=True),
              patch.object(runtime.sys, "argv", [
                  "verify_ci_runner.py", "--config-json-env", "CI_RUNNER_PROFILES_JSON",
                  "--profile", self.profile.id, "--label", self.profile.labels[0], "--runner-id", "123",
              ]),
              patch.object(runtime.socket, "gethostname", return_value=self.profile.expected_host),
              patch.object(Path, "stat", root_owned),
              patch.object(runtime.subprocess, "run", side_effect=docker_without_profile_secret),
              patch.object(runtime, "inspect_capacity", side_effect=OSError(str(self.root))) as capacity,
              contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors)):
            result = runtime.main()
        self.assertEqual(1, result)
        self.assertIn("OSError", errors.getvalue())
        self.assertNotIn(str(self.root), errors.getvalue())
        capacity.assert_called_once_with(self.profile)


if __name__ == "__main__":
    unittest.main()
