#!/usr/bin/env python3
"""Audit GitHub Actions workflows for the zero-cost runner and storage policy."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import operator
from pathlib import Path
import re
import sys
from typing import Any

import yaml


ARTIFACT_UPLOAD_ACTION = "actions/upload-artifact"
CACHE_ACTION = "actions/cache"
REPORT_STORE_PATH = Path("Scripts/CI/ci_report_store.py")
GHA_CACHE_RE = re.compile(r"\btype\s*=\s*gha\b", re.IGNORECASE)
ARTIFACT_UPLOAD_RE = re.compile(r"\bupload-artifact\b", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _assigned_value(tree: ast.Module, name: str) -> ast.expr | None:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return node.value
    return None


def _assigned_string(tree: ast.Module, name: str) -> str | None:
    value = _assigned_value(tree, name)
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _integer_expression(node: ast.expr | None) -> int | None:
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.BinOp):
        operations = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.FloorDiv: operator.floordiv,
        }
        function = operations.get(type(node.op))
        left = _integer_expression(node.left)
        right = _integer_expression(node.right)
        if function is not None and left is not None and right is not None and right != 0:
            return function(left, right)
    return None


def _timedelta_days(node: ast.expr | None) -> int | None:
    if not isinstance(node, ast.Call) or _call_name(node.func) != "timedelta":
        return None
    for keyword in node.keywords:
        if keyword.arg == "days":
            return _integer_expression(keyword.value)
    return None


def _function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return next(
        (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name),
        None,
    )


def _call_contains_names(node: ast.AST, function_name: str, expected_names: set[str]) -> bool:
    return any(
        isinstance(call, ast.Call)
        and _call_name(call.func) == function_name
        and expected_names.issubset({argument.id for argument in call.args if isinstance(argument, ast.Name)})
        for call in ast.walk(node)
    )


def _manifest_binds_repository(function: ast.FunctionDef | ast.AsyncFunctionDef, repository_names: set[str]) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Compare) or not any(isinstance(operation, ast.NotEq) for operation in node.ops):
            continue
        call = node.left
        if not isinstance(call, ast.Call) or _call_name(call.func) != "get" or not isinstance(call.func, ast.Attribute):
            continue
        if not isinstance(call.func.value, ast.Name) or call.func.value.id != "value":
            continue
        if not call.args or not isinstance(call.args[0], ast.Constant) or call.args[0].value != "repository":
            continue
        if any(isinstance(comparator, ast.Name) and comparator.id in repository_names for comparator in node.comparators):
            return True
    return False


def _manifest_validates_run_attempt(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "_validate_identity":
            continue
        fields = {
            argument.slice.value
            for argument in node.args
            if isinstance(argument, ast.Subscript)
            and isinstance(argument.value, ast.Name)
            and argument.value.id == "value"
            and isinstance(argument.slice, ast.Constant)
            and isinstance(argument.slice.value, str)
        }
        if {"run_id", "attempt"}.issubset(fields):
            return True
    return False


def _report_store_findings(source: str, location: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(source, filename=location)
    except SyntaxError as error:
        return [Finding(location, f"local report store is not valid Python: {error.msg}")]

    expected_limits = {
        "DEFAULT_MAX_BYTES": 1024 * 1024 * 1024,
    }
    for constant, expected in expected_limits.items():
        actual = _integer_expression(_assigned_value(tree, constant))
        if actual != expected:
            findings.append(Finding(location, f"{constant} must enforce the 1 GiB local report-store cap"))

    for constant, days in (("SUCCESS_RETENTION", 3), ("FAILURE_RETENTION", 7)):
        actual = _timedelta_days(_assigned_value(tree, constant))
        if actual != days:
            findings.append(Finding(location, f"{constant} must retain reports for {days} days"))

    root_function = _function(tree, "default_root")
    repository_constant = _assigned_string(tree, "REPOSITORY") or _assigned_string(tree, "DEFAULT_REPOSITORY")
    static_repository = None
    if repository_constant and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository_constant):
        owner, name = repository_constant.split("/", 1)
        if owner not in {".", ".."} and name not in {".", ".."}:
            static_repository = (owner, name)

    if root_function is None:
        findings.append(Finding(location, "local report store must define repository-scoped default_root"))
    else:
        nodes = list(ast.walk(root_function))
        strings = {node.value for node in nodes if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        repository_validation = any(
            isinstance(node, ast.Call)
            and _call_name(node.func) == "_validate_repository"
            and any(isinstance(argument, ast.Name) and argument.id == "selected" for argument in node.args)
            for node in nodes
        )
        returns = [node.value for node in nodes if isinstance(node, ast.Return) and node.value is not None]
        return_strings = {
            node.value
            for expression in returns
            for node in ast.walk(expression)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        return_names = {
            child.id
            for expression in returns
            for child in ast.walk(expression)
            if isinstance(child, ast.Name)
        }
        dynamic_scope = (
            "GITHUB_REPOSITORY" in strings
            and repository_validation
            and {"owner", "name"}.issubset(return_names)
        )
        static_scope = static_repository is not None and any(
            static_repository[1].lower() in value.lower() for value in return_strings
        )
        if not dynamic_scope and not static_scope:
            findings.append(Finding(location, "local report root must be namespaced by the validated GitHub repository"))

    manifest_function = _function(tree, "_read_manifest")
    required_manifest_fields = {"repository", "run_id", "attempt"}
    manifest_sets = []
    if manifest_function is not None:
        for node in ast.walk(manifest_function):
            if isinstance(node, ast.Set):
                manifest_sets.append({
                    item.value for item in node.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                })
    if not any(required_manifest_fields.issubset(fields) for fields in manifest_sets) or manifest_function is None or not _manifest_binds_repository(
        manifest_function, {"repository", "REPOSITORY"}
    ) or not _manifest_validates_run_attempt(manifest_function):
        findings.append(Finding(location, "local report manifest must validate repository, run, and attempt ownership"))

    save_function = _function(tree, "save_report")
    if save_function is None:
        findings.append(Finding(location, "local report store must define save_report"))
    else:
        arguments = save_function.args
        parameters = {
            argument.arg
            for argument in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
        }
        identity_validated = _call_contains_names(save_function, "_validate_identity", {"run_id", "attempt"})
        if not {"run_id", "attempt"}.issubset(parameters) or not identity_validated:
            findings.append(Finding(location, "save_report must validate run and attempt identity"))
        if "repository" in parameters:
            if not _call_contains_names(save_function, "_validate_repository", {"repository"}):
                findings.append(Finding(location, "save_report must validate its repository identity"))
        elif static_repository is None or not any(
            isinstance(node, ast.Name) and node.id == "REPOSITORY" for node in ast.walk(save_function)
        ):
            findings.append(Finding(location, "save_report must bind a validated static repository identity"))
    return findings


def _flatten_labels(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip().lower()]
    if isinstance(value, list):
        return [label for item in value for label in _flatten_labels(item)]
    if isinstance(value, dict):
        return [label for item in value.values() for label in _flatten_labels(item)]
    return []


def _is_hosted_label(label: str) -> bool:
    if label.startswith(("ubuntu-", "windows-", "macos-")):
        return True
    return bool(re.search(r"(?:^|[-_])(?:large|xlarge|[2-9]xlarge|[1-9][0-9]+xlarge)(?:$|[-_])", label))


def _truthy(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str) and value.strip().lower() in {"", "false", "no", "off", "0"}:
        return False
    return bool(value)


def _contains_gha_cache(value: Any) -> bool:
    if isinstance(value, str):
        return bool(GHA_CACHE_RE.search(value))
    if isinstance(value, dict):
        return any(_contains_gha_cache(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_gha_cache(item) for item in value)
    return False


def _safe_relative(root: Path, reference: str) -> Path | None:
    if not reference.startswith("./"):
        return None
    candidate = (root / reference[2:]).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


class WorkflowPolicy:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.findings: list[Finding] = []
        self.visited_workflows: set[Path] = set()
        self.active_workflows: set[Path] = set()
        self.visited_actions: set[Path] = set()
        self.active_actions: set[Path] = set()
        self.report_store_requires_explicit_repository = True

    def _location(self, path: Path, detail: str = "") -> str:
        try:
            relative = path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            relative = str(path)
        return f"{relative}{detail}"

    def _load_yaml(self, path: Path) -> dict[str, Any] | None:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
            self.findings.append(Finding(self._location(path), f"cannot parse YAML: {error}"))
            return None
        if not isinstance(value, dict):
            self.findings.append(Finding(self._location(path), "YAML document must contain a mapping"))
            return None
        return value

    def _is_free_codeql_job(self, workflow: Path, job_id: str) -> bool:
        try:
            relative = workflow.resolve().relative_to(self.root).as_posix().lower()
        except ValueError:
            return False
        return relative == ".github/workflows/codeql.yml" and job_id == "analyze"

    def _check_runner(self, workflow: Path, job_id: str, job: dict[str, Any]) -> None:
        location = self._location(workflow, f" jobs.{job_id}.runs-on")
        labels = _flatten_labels(job.get("runs-on"))
        if not labels:
            self.findings.append(Finding(location, "job must declare an inspectable runner"))
            return

        hosted_labels = [label for label in labels if _is_hosted_label(label)]
        if self._is_free_codeql_job(workflow, job_id):
            condition = str(job.get("if", "")).strip()
            if labels != ["ubuntu-latest"]:
                self.findings.append(Finding(location, "public CodeQL exception must use ubuntu-latest only"))
            if condition.startswith("${{") and condition.endswith("}}"):
                condition = condition[3:-2].strip()
            if re.sub(r"\s+", "", condition) != "!github.event.repository.private":
                self.findings.append(Finding(location, "hosted CodeQL job must skip private repository clones"))
            return

        if "self-hosted" not in labels:
            self.findings.append(Finding(location, "app and maintenance jobs must target self-hosted runners"))
        if hosted_labels:
            self.findings.append(Finding(location, f"hosted runner labels are forbidden here: {hosted_labels}"))

    def _check_step(self, workflow: Path, detail: str, step: dict[str, Any]) -> None:
        location = self._location(workflow, detail)
        uses = step.get("uses")
        if isinstance(uses, str):
            if uses.startswith("./"):
                self._analyze_local_action(workflow, uses)
            else:
                action = uses.split("@", 1)[0].strip().lower()
                if action == ARTIFACT_UPLOAD_ACTION or action.startswith(ARTIFACT_UPLOAD_ACTION + "/"):
                    self.findings.append(Finding(location, f"routine cloud artifact upload is forbidden: {action}"))
                if action == CACHE_ACTION or action.startswith(CACHE_ACTION + "/"):
                    self.findings.append(Finding(location, f"GitHub Actions cache action is forbidden: {action}"))

                inputs = step.get("with", {})
                if not isinstance(inputs, dict):
                    inputs = {}
                if action == "actions/setup-go":
                    cache = inputs.get("cache")
                    if cache is None or _truthy(cache):
                        self.findings.append(Finding(location, "setup-go Actions cache must be disabled with cache: false"))
                if action in {"actions/setup-node", "actions/setup-dotnet"}:
                    if _truthy(inputs.get("cache")) or _truthy(inputs.get("cache-dependency-path")):
                        self.findings.append(Finding(location, f"implicit dependency cache is forbidden for {action}"))
                if action == "docker/build-push-action" and _contains_gha_cache(inputs):
                    self.findings.append(Finding(location, "Docker build cache must not use type=gha"))
                if _contains_gha_cache(inputs):
                    self.findings.append(Finding(location, "GitHub Actions cache backend type=gha is forbidden"))

        run = step.get("run")
        if isinstance(run, str):
            if ARTIFACT_UPLOAD_RE.search(run):
                self.findings.append(Finding(location, "workflow shell step references cloud artifact upload"))
            if GHA_CACHE_RE.search(run):
                self.findings.append(Finding(location, "workflow shell step uses GitHub Actions cache backend type=gha"))
            if "ci_report_store.py" in run and re.search(r"\b(?:save|prune)\b", run):
                if self.report_store_requires_explicit_repository and not re.search(r"--repository(?:\s|=)", run):
                    self.findings.append(Finding(location, "local report-store workflow call must pass --repository explicitly"))

    def _analyze_steps(self, workflow: Path, steps: Any, prefix: str) -> None:
        if not isinstance(steps, list):
            self.findings.append(Finding(self._location(workflow, prefix), "steps must be a YAML list"))
            return
        for index, step in enumerate(steps):
            detail = f"{prefix}[{index}]"
            if not isinstance(step, dict):
                self.findings.append(Finding(self._location(workflow, detail), "step must be a YAML mapping"))
                continue
            self._check_step(workflow, detail, step)

    def _analyze_local_action(self, source: Path, reference: str) -> None:
        action_path = _safe_relative(self.root, reference)
        location = self._location(source, f" uses={reference}")
        if action_path is None:
            self.findings.append(Finding(location, "local action path escapes repository root"))
            return
        if action_path.is_dir():
            metadata = next(
                (candidate for candidate in (action_path / "action.yml", action_path / "action.yaml") if candidate.is_file()),
                None,
            )
        elif action_path.is_file():
            metadata = action_path
        else:
            metadata = None
        if metadata is None:
            self.findings.append(Finding(location, "local action metadata is missing; policy cannot inspect it"))
            return
        metadata = metadata.resolve()
        if metadata in self.active_actions:
            self.findings.append(Finding(self._location(metadata), "local composite action cycle detected"))
            return
        if metadata in self.visited_actions:
            return
        document = self._load_yaml(metadata)
        if document is None:
            return
        runs = document.get("runs")
        if not isinstance(runs, dict) or runs.get("using") != "composite":
            self.findings.append(Finding(self._location(metadata), "local non-composite actions require explicit policy review"))
            return
        self.active_actions.add(metadata)
        try:
            self._analyze_steps(metadata, runs.get("steps"), " runs.steps")
        finally:
            self.active_actions.remove(metadata)
            self.visited_actions.add(metadata)

    def _analyze_workflow(self, workflow: Path) -> None:
        workflow = workflow.resolve()
        if workflow in self.active_workflows:
            self.findings.append(Finding(self._location(workflow), "local reusable workflow cycle detected"))
            return
        if workflow in self.visited_workflows:
            return
        document = self._load_yaml(workflow)
        if document is None:
            return
        jobs = document.get("jobs")
        if not isinstance(jobs, dict) or not jobs:
            self.findings.append(Finding(self._location(workflow), "workflow must declare at least one job"))
            return

        self.active_workflows.add(workflow)
        try:
            for job_id, job in jobs.items():
                job_location = self._location(workflow, f" jobs.{job_id}")
                if not isinstance(job, dict):
                    self.findings.append(Finding(job_location, "job must be a YAML mapping"))
                    continue
                reusable = job.get("uses")
                if isinstance(reusable, str):
                    if "runs-on" in job:
                        self.findings.append(Finding(job_location, "reusable workflow call cannot define runs-on"))
                    if not reusable.startswith("./.github/workflows/"):
                        self.findings.append(Finding(job_location, "external reusable workflow is not inspectable"))
                        continue
                    reusable_path = _safe_relative(self.root, reusable)
                    if reusable_path is None or not reusable_path.is_file():
                        self.findings.append(Finding(job_location, f"local reusable workflow is missing: {reusable}"))
                        continue
                    self._analyze_workflow(reusable_path)
                    continue

                self._check_runner(workflow, str(job_id), job)
                self._analyze_steps(workflow, job.get("steps"), f" jobs.{job_id}.steps")
        finally:
            self.active_workflows.remove(workflow)
            self.visited_workflows.add(workflow)

    def audit(self) -> list[Finding]:
        store_path = self.root / REPORT_STORE_PATH
        try:
            store_source = store_path.read_text(encoding="utf-8-sig")
        except OSError:
            self.findings.append(Finding(REPORT_STORE_PATH.as_posix(), "repository-scoped local report store is missing"))
        else:
            self.findings.extend(_report_store_findings(store_source, REPORT_STORE_PATH.as_posix()))
            try:
                store_tree = ast.parse(store_source, filename=REPORT_STORE_PATH.as_posix())
            except SyntaxError:
                pass
            else:
                save_function = _function(store_tree, "save_report")
                if save_function is not None:
                    arguments = save_function.args
                    parameters = {
                        argument.arg
                        for argument in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
                    }
                    self.report_store_requires_explicit_repository = "repository" in parameters

        workflows = self.root / ".github" / "workflows"
        if not workflows.is_dir():
            self.findings.append(Finding(".github/workflows", "workflow directory is missing"))
        else:
            files = sorted([*workflows.rglob("*.yml"), *workflows.rglob("*.yaml")])
            if not files:
                self.findings.append(Finding(".github/workflows", "no workflow YAML files were found"))
            for workflow in files:
                self._analyze_workflow(workflow)

        return self.findings


def audit_repository(root: Path) -> list[Finding]:
    return WorkflowPolicy(root).audit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    findings = audit_repository(args.repo_root)
    if findings:
        for finding in findings:
            print(f"FAIL {finding}", file=sys.stderr)
        print(f"Workflow policy failed with {len(findings)} violation(s)", file=sys.stderr)
        return 1
    print("Workflow policy passed: self-hosted app jobs, public-only hosted CodeQL, no cloud artifact uploads/caches, scoped local reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
