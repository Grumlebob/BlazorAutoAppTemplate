#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from doc_slice_loader import (
    DOC_OWNER_PATHS,
    CLUSTER_ENTRY,
    FORK_ENTRY,
    DocumentSliceError,
    fence_error,
    load_document_slices,
    missing_literal,
    missing_section_literal,
    missing_target_scripts,
)


ROOT = Path(__file__).resolve().parents[5]
failures: list[str] = []


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def fail(message: str) -> None:
    failures.append(message)


def require_file(path: str) -> None:
    if not exists(path):
        fail(f"missing required deployment file: {path}")


def require_contains(path: str, needle: str, why: str) -> None:
    text = read(path)
    if needle not in text:
        fail(f"{path}: missing {why}: {needle}")


def require_not_contains(path: str, needle: str, why: str) -> None:
    text = read(path)
    if needle in text:
        fail(f"{path}: contains forbidden {why}: {needle}")


def normalize_workflow_text(text: str) -> str:
    return re.sub(r"\\\r?\n[ \t]*", " ", text)


def workflow_step_text(workflow: str, step_name: str) -> str:
    normalized = normalize_workflow_text(workflow)
    match = re.search(
        rf"(?ms)^      - name: {re.escape(step_name)}\r?\n.*?(?=^      - name: |\Z)",
        normalized,
    )
    return match.group(0) if match else ""


def tracked_files() -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        fail(f"unable to inspect tracked files with git ls-files: {exc}")
        return set()
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        path = line.strip().replace("\\", "/")
        if path and (ROOT / path).exists():
            paths.add(path)
    return paths


def deployment_text_files() -> list[Path]:
    roots = [ROOT / "Deployment", ROOT / ".github"]
    suffixes = {".yml", ".yaml", ".j2", ".sh", ".py", ".json", ".cs", ".csproj"}
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in suffixes:
                files.append(path)
    return files


required_files = [
    "Deployment/Common/README.md",
    "Deployment/Common/release.yml",
    "Deployment/Common/ci-python-constraints.txt",
    "Deployment/LocalCluster/Scripts/ci-docker-smoke.sh",
    "Deployment/LocalCluster/Scripts/Tests/test-ci-docker-smoke.sh",
    "Deployment/LocalCluster/Scripts/Tests/test_doc_slice_loader.py",
    "Scripts/CI/validate-frontend-profiles.sh",
    "Scripts/CI/validate_dotnet_test_results.py",
    "Scripts/CI/tests/test_validate_dotnet_test_results.py",
    "Deployment/LocalCluster/Scripts/check-node-main-capacity.sh",
    "Deployment/LocalCluster/Scripts/localcluster-capacity-thresholds.sh",
    "Scripts/CI/check-runner-capacity.sh",
    ".github/workflows/localcluster-docker-maintenance.yml",
    "Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh",
    "Deployment/Common/Scripts/prune-actions-runner-residue.sh",
    "Deployment/LocalCluster/Scripts/prune-cluster-docker-residue.sh",
    "Deployment/LocalCluster/Scripts/prune-ci-residue.py",
    "Deployment/Common/Scripts/validate_release_manifest.py",
    "Deployment/Common/Scripts/Tests/test_ci_provenance.py",
    "Deployment/Common/Scripts/Tests/test_target_gate.py",
    "Deployment/Common/Scripts/Tests/test_release_contract.py",
    "Deployment/Common/Scripts/Tests/test_pin_release_payload.py",
    "Deployment/LocalCluster/Scripts/verify-release-identity.sh",
    "Deployment/LocalCluster/Scripts/Tests/test-verify-release-identity.sh",
    "Deployment/LocalCluster/Scripts/prune-migration-artifacts.sh",
    "Deployment/LocalCluster/Scripts/Component/lib/read-live-release-ci-run-ids.py",
    "Deployment/LocalCluster/Scripts/Tests/test_read_live_release_ci_run_ids.py",
    "Deployment/LocalSingleNode/Scripts/verify-release-identity.sh",
    "Deployment/LocalSingleNode/Scripts/Tests/test-verify-release-identity.sh",
    "Deployment/LocalSingleNode/Scripts/lib/acceptance_profile.sh",
    "Deployment/LocalSingleNode/Scripts/lib/read_release_acceptance.py",
    "Deployment/LocalSingleNode/Scripts/Tests/test_release_acceptance.py",
    "Deployment/LocalSingleNode/Scripts/Tests/test_pin_legacy_release.py",
    "Deployment/LocalSingleNode/Scripts/pin-legacy-release.py",
    ".github/workflows/pin-localsinglenode-legacy-release.yml",
    "Scripts/Test-DeployedSite.ps1",
    "Scripts/CI/tests/test_deployed_site_acceptance.py",
    "Scripts/CI/migration_staging_artifact.py",
    "Scripts/CI/tests/test_migration_staging_artifact.py",
    "Scripts/CI/ci_report_store.py",
    "Scripts/CI/tests/test_ci_report_store.py",
    "Deployment/Common/Scripts/install-ansible.sh",
    "Deployment/Common/Scripts/prune-actions-artifacts.sh",
    "Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py",
    "Deployment/Common/Scripts/Component/lib/pin_release_payload.py",
    "Deployment/Common/Scripts/Component/lib/import_legacy_release_payload.py",
    "Deployment/Common/Scripts/Tests/test_import_legacy_release_payload.py",
    "Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py",
    "Deployment/Common/Scripts/read-release-setting.sh",
    "Deployment/Common/Scripts/validate-common-release.sh",
    "Deployment/Common/Scripts/Component/lib/read-release-setting.py",
    "Deployment/Common/Scripts/Component/lib/release_settings.py",
    "Deployment/Common/Scripts/Component/lib/release_manifest.py",
    "Deployment/Common/Scripts/Component/lib/simple_yaml.py",
    "Deployment/Common/Scripts/Component/lib/account_deploy_settings.py",
    "Deployment/Common/Scripts/Component/lib/validate-common-release.py",
    "Deployment/LocalCluster/HowToDeployLocalCluster.md",
    ".github/workflows/ci.yml",
    ".github/workflows/cd-localcluster.yml",
    ".yamllint.yml",
    ".config/dotnet-tools.json",
    ".gitignore",
    "Deployment/LocalCluster/machines.example.yml",
    "Deployment/LocalCluster/inventory/prod/hosts.yml",
    "Deployment/LocalCluster/inventory/prod/group_vars/all.yml",
    "Deployment/LocalCluster/inventory/prod/vault.example.yml",
    "Deployment/LocalCluster/ansible/ansible.cfg",
    "Deployment/LocalCluster/ansible/playbooks/PrepareExistingLocalClusterApp.yml",
    "Deployment/LocalCluster/ansible/playbooks/PrepareFreshLinuxMachine.yml",
    "Deployment/LocalCluster/ansible/playbooks/site.yml",
    "Deployment/LocalCluster/ansible/roles/app/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/app/templates/app.env.j2",
    "Deployment/Common/ansible/roles/app_marker/tasks/main.yml",
    "Deployment/Common/ansible/roles/app_marker/templates/app-marker.env.j2",
    "Deployment/LocalCluster/ansible/roles/caddy/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/caddy/templates/app.caddy.j2",
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "Deployment/Common/ansible/roles/docker/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/firewall/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2",
    "Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.service.j2",
    "Deployment/Common/ansible/roles/mint_base/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/postgres/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/postgres/templates/node-db.env.j2",
    "Deployment/LocalCluster/ansible/roles/redis/tasks/main.yml",
    "Deployment/Common/ansible/roles/ssh_hardening/tasks/main.yml",
    "Deployment/LocalCluster/compose/app-server/docker-compose.yml",
    "Deployment/LocalCluster/compose/node-db/docker-compose.yml",
    "Deployment/LocalCluster/Scripts/README.md",
    "Deployment/LocalCluster/Scripts/acceptance-check.sh",
    "Deployment/LocalCluster/Scripts/bootstrap-node.sh",
    "Deployment/LocalCluster/Scripts/check-cloudflare-tunnel.sh",
    "Deployment/LocalCluster/Scripts/check-github-runner.sh",
    "Deployment/LocalCluster/Scripts/check-port-collisions.sh",
    "Deployment/LocalCluster/Scripts/check-vault.sh",
    "Deployment/LocalCluster/Scripts/deploy.sh",
    "Deployment/LocalCluster/Scripts/doctor.sh",
    "Deployment/LocalCluster/Scripts/discover-machines.sh",
    "Deployment/Common/Scripts/ensure-actions-runner-prereqs.sh",
    "Deployment/LocalCluster/Scripts/audit-deployment.sh",
    "Deployment/LocalCluster/Scripts/find-successful-ci-run.sh",
    "Deployment/LocalCluster/Scripts/generate-inventory.sh",
    "Deployment/LocalCluster/Scripts/install-github-runner.sh",
    "Deployment/LocalCluster/Scripts/install-ansible.sh",
    "Deployment/LocalCluster/Scripts/read-deploy-setting.sh",
    "Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py",
    "Deployment/LocalCluster/Scripts/Component/lib/doc_slice_loader.py",
    "Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py",
    "Deployment/LocalCluster/Scripts/Component/lib/generate-inventory.py",
    "Deployment/LocalCluster/Scripts/Component/lib/read-deploy-setting.py",
    "Deployment/LocalCluster/Scripts/Component/lib/validate-deploy-settings.py",
    "Deployment/LocalCluster/Scripts/Component/lib/validate-vault.py",
    "Deployment/Common/Scripts/Tests/test_account_deploy_settings.py",
    "Deployment/Cloud/Scripts/Tests/test-cloud-account-env.sh",
    "Deployment/Cloud/Scripts/Component/lib/cloud-env.sh",
    "Deployment/Cloud/Scripts/Component/lib/cloud_settings.py",
    "Deployment/Cloud/Scripts/deploy.sh",
    "Deployment/Cloud/Scripts/configure-github-environment.sh",
    "Deployment/Cloud/ansible/roles/app/tasks/main.yml",
    "Deployment/Cloud/ansible/roles/app/templates/app.env.j2",
    "Deployment/Cloud/compose/app-server/docker-compose.yml",
    "Deployment/Cloud/inventory/prod/group_vars/all.yml",
    "Deployment/LocalCluster/Scripts/Component/node-db/backup-db.sh",
    "Deployment/LocalCluster/Scripts/Component/node-db/restore-db.sh",
    "Deployment/LocalCluster/Scripts/preflight.sh",
    "Deployment/LocalCluster/Scripts/prepare-existing-localcluster-app.sh",
    "Deployment/LocalCluster/Scripts/prepare-fresh-linux-machines.sh",
    "Deployment/LocalCluster/Scripts/prune-docker-residue.sh",
    "Deployment/LocalCluster/Scripts/list-deployed-apps.sh",
    "Deployment/LocalCluster/Scripts/report-nodes.sh",
    "Deployment/LocalCluster/Scripts/setup-cloudflare-tunnel.sh",
    "Deployment/LocalCluster/Scripts/setup-control-machine.sh",
    "Deployment/LocalCluster/Scripts/setup-secrets.sh",
    "Deployment/LocalCluster/Scripts/Component/ping-fresh-machines.sh",
    "Deployment/Common/Scripts/Component/with-deploy-lock.sh",
    "Deployment/LocalCluster/Scripts/Component/with-node-main-deploy-lock.sh",
    "Deployment/LocalCluster/Scripts/status.sh",
    "Deployment/LocalCluster/Scripts/summary.sh",
    "Deployment/LocalCluster/Scripts/validate-deploy-settings.sh",
    "Deployment/LocalCluster/Scripts/validate-machines.sh",
    "Deployment/LocalCluster/Scripts/validate-rendered-templates.sh",
    "Deployment/LocalCluster/Scripts/validate-side-by-side.sh",
    "Deployment/LocalCluster/Scripts/verify-bootstrap.sh",
    "Deployment/LocalCluster/Scripts/verify-backup.sh",
    "Deployment/Common/Scripts/with-deploy-lock.sh",
    "Deployment/Common/Scripts/release-deploy-lock.sh",
    "Deployment/Common/Scripts/Tests/test-with-deploy-lock.sh",
    ".github/workflows/auto-merge-dependabot.yml",
    ".github/workflows/cd-cloud.yml",
    "BlazorAutoApp/Program.cs",
    "BlazorAutoApp/BlazorAutoApp.csproj",
]
required_files.extend([
    "Deployment/Common/caddy/Caddyfile",
    "Deployment/Common/ansible/roles/caddy_install/tasks/main.yml",
    "Deployment/Common/ansible/roles/caddy_install/handlers/main.yml",
    "Deployment/LocalCluster/ansible/roles/caddy/meta/main.yml",
    "Deployment/Common/Scripts/Tests/test-ensure-actions-runner-prereqs.sh",
    "Deployment/Common/Scripts/Component/lib/release_status.py",
    "Deployment/Common/Scripts/Tests/test_release_status.py",
    "Deployment/LocalCluster/Scripts/release-status.py",
    "Deployment/LocalCluster/Scripts/Tests/test_release_status.py",
    "Deployment/LocalSingleNode/Scripts/release-status.py",
    "Deployment/LocalSingleNode/Scripts/Tests/test_release_status.py",
    ".github/workflows/release-status.yml",
])
for file in required_files:
    require_file(file)

legacy_pin_helper = read("Deployment/LocalSingleNode/Scripts/pin-legacy-release.py")
for needle, why in [
    ("def _verify_offline_restore(", "recovery pin is exercised through the offline restore path"),
    ('os.environ.pop("GITHUB_TOKEN", None)', "GitHub artifact credentials are unavailable during the restore drill"),
    ("pin_release_payload.restore(", "recovery is restored from the owned local pin"),
    ("sha256_file(restored_file) != digest", "restored recovery payload checksums are verified"),
    ('"offline_restore": "verified"', "workflow reports the offline restore result"),
    ('selection.get("outcome") not in {"legacy_artifact", "success"}', "exact successful receipts do not hide still-retained legacy artifacts"),
    ('"app_image_digest": summary["digest"]', "any successful receipt is bound to the accepted legacy image digest"),
]:
    if needle not in legacy_pin_helper:
        fail(f"Deployment/LocalSingleNode/Scripts/pin-legacy-release.py: missing {why}")


removed_files = [
    "HowToDeploy.md",
    "DeploymentRefactor.md",
    "SideBySide.md",
    ".ansible-lint.yml",
    ".github/workflows/deploy-lan.yml",
    "Deployment/LocalCluster/.deploy.local.env.example",
    "Deployment/LocalCluster/Scripts/audit_deployment.py",
    "Deployment/LocalCluster/Scripts/backup-db.sh",
    "Deployment/LocalCluster/Scripts/deploy_settings.py",
    "Deployment/LocalCluster/Scripts/discover-node.sh",
    "Deployment/LocalCluster/Scripts/generate-inventory.py",
    "Deployment/LocalCluster/Scripts/health-check.sh",
    "Deployment/LocalCluster/Scripts/ping-fresh-machines.sh",
    "Deployment/LocalCluster/Scripts/read-deploy-setting.py",
    "Deployment/LocalCluster/Scripts/restore-db.sh",
    "Deployment/LocalCluster/Scripts/validate-deploy-settings.py",
    "Deployment/LocalCluster/Scripts/validate-vault.py",
    "Deployment/LocalCluster/caddy/sites/app.caddy",
    "Deployment/LocalCluster/compose/load-balancer/docker-compose.yml",
    "Deployment/LocalCluster/inventory/prod/group_vars/app_servers.yml",
    "Deployment/LocalCluster/inventory/prod/group_vars/load_balancer.yml",
    "Deployment/LocalCluster/inventory/prod/group_vars/node_db.yml",
    "Deployment/LocalCluster/inventory/prod/host_vars/node-app1.yml",
    "Deployment/LocalCluster/inventory/prod/host_vars/node-app2.yml",
    "Deployment/LocalCluster/inventory/prod/host_vars/node-db.yml",
    "Deployment/LocalCluster/inventory/prod/host_vars/node-main.yml",
    "Deployment/LocalCluster/ansible/playbooks/app-server.yml",
    "Deployment/LocalCluster/ansible/playbooks/load-balancer.yml",
    "Deployment/LocalCluster/ansible/playbooks/migrate.yml",
    "Deployment/LocalCluster/ansible/playbooks/node-db.yml",
]
for file in removed_files:
    if exists(file):
        fail(f"stale deployment file should be removed: {file}")

old_layout_paths = [
    "Deployment/ansible",
    "Deployment/caddy",
    "Deployment/compose",
    "Deployment/inventory",
    "Deployment/scripts",
    "Deployment/machines.example.yml",
    "Deployment/machines.yml",
]
for path in old_layout_paths:
    if exists(path):
        fail(f"old deployment layout path should not exist: {path}")


try:
    cluster_guide_documents = load_document_slices(ROOT, CLUSTER_ENTRY)
except DocumentSliceError as exc:
    fail(str(exc))
    cluster_guide_documents = {CLUSTER_ENTRY: read(CLUSTER_ENTRY) if exists(CLUSTER_ENTRY) else ""}

try:
    fork_guide_documents = load_document_slices(ROOT, FORK_ENTRY)
except DocumentSliceError as exc:
    fail(str(exc))
    fork_guide_documents = {FORK_ENTRY: read(FORK_ENTRY) if exists(FORK_ENTRY) else ""}

for document_path, document_text in cluster_guide_documents.items():
    error = fence_error(document_path, document_text)
    if error:
        fail(error)

for forbidden in [
    ".deploy.local",
    "discover-node",
    "health-check",
    "Deployment/LocalCluster/compose/load-balancer",
    "Deployment/LocalCluster/caddy/sites/app.caddy",
    "Deployment/LocalCluster/inventory/prod/host_vars",
]:
    for document_path, document_text in cluster_guide_documents.items():
        if forbidden in document_text:
            fail(f"{document_path}: contains stale deployment reference: {forbidden}")

for document_path, document_text in cluster_guide_documents.items():
    for error in missing_target_scripts(ROOT, document_path, document_text):
        fail(error)

for needle, why, owner in [
    ('Reserve LAN IPs', 'dedicated router IP reservation step', 'setup'),
    ('Generate Inventory', 'dedicated control-machine inventory generation step', 'setup'),
    ('Ensure all four nodes are using their reserved IPs before proceeding.', 'router reservation checkpoint', 'setup'),
    ('validate-machines.sh', 'machines.yml validation checkpoint before inventory generation', 'setup'),
    ('Success: prints OK lines for machines.yml, deployment settings, and all four nodes.', 'machines validation success checkpoint', 'setup'),
    ('Run this only from a full repository checkout on the control machine.', 'verify-bootstrap full-checkout warning', 'setup'),
    ('test -f "$REPO_ROOT/Deployment/LocalCluster/Scripts/verify-bootstrap.sh"', 'verify-bootstrap dependency checkpoint', 'setup'),
    ('Configure The GitHub CD Environment', 'dedicated GitHub environment setup step', 'setup'),
    ('New environment -> localcluster', 'localcluster environment creation', 'setup'),
    ('Deployment branches and tags: Selected branches and tags', 'deployment branch restriction instructions', 'setup'),
    ('Allowed branch: main', 'main-only environment branch rule', 'setup'),
    ('Environment localcluster exists and allows deployments from main.', 'environment setup checkpoint', 'setup'),
    ('First Deploy From GitHub Actions', 'first CD deploy step after environment setup', 'setup'),
    ('Main CI publishes the application image, a digest-pinned GHCR payload', 'main-only CI publishing explanation', 'release_contract'),
    ('Optional sanity check: before deploying, confirm the image tag exists.', 'optional image check wording', 'setup'),
    ('if the GHCR payload is missing or cannot be retrieved', 'missing immutable payload recovery guidance', 'release_contract'),
    ('pins PostgreSQL and Redis to exact versioned image tags', 'pinned database image guidance', 'settings'),
    ('If this is the only app on these four nodes, keep the default ports and continue.', 'single-site default guidance', 'settings'),
    ('If another LocalCluster app already runs on these nodes', 'side-by-side settings warning', 'fork_existing'),
    ('## Choose side by side or replacement', 'existing-cluster fork identity choice', 'fork_existing'),
    ('For a second fork on the same nodes, do not reuse these values from the first app', 'unique side-by-side values list', 'fork_existing'),
    ('Second-fork flow on already-prepared nodes', 'second-fork execution flow', 'fork_existing'),
    ('prepare-existing-localcluster-app.sh', 'existing cluster app preparation guidance', 'fork_existing'),
    ('Do not rerun `bootstrap-node.sh` or `prepare-fresh-linux-machines.sh` for already-prepared nodes', 'side-by-side rerun warning', 'fork_existing'),
    ("this fork's deploy key is installed on the nodes", 'side-by-side validation ordering warning', 'fork_existing'),
    ('same Cloudflare account', 'shared tunnel Cloudflare account limitation', 'fork_existing'),
    ('gh repo clone "$LOCALCLUSTER_REPO"', 'fork-safe clone command', 'setup'),
    ('gh repo view --json nameWithOwner,url,defaultBranchRef', 'repository identity checkpoint', 'setup'),
    ('Deployment identity checkpoint', 'deployment identity checkpoint before setup', 'setup'),
    ('git add Deployment/LocalCluster/inventory/prod/group_vars/all.yml', 'deployment settings commit command', 'settings'),
    ('needs committed `all.yml` settings and committed `hosts.yml` inventory', 'committed settings and inventory explanation', 'settings'),
    ('git status --short Deployment/LocalCluster/inventory/prod/group_vars/all.yml Deployment/LocalCluster/inventory/prod/hosts.yml Deployment/LocalCluster/inventory/prod/vault.yml', 'pre-push deployment file clean-state check', 'settings'),
    ('main publisher job needs `packages: write`', 'job-scoped GitHub Actions package write prerequisite', 'release_contract'),
    ('`app_image`', 'side-by-side app image uniqueness', 'settings'),
    ('`migration_bundle_name`', 'side-by-side migration bundle uniqueness', 'settings'),
    ('same machine IPs', 'side-by-side reused machine IP guidance', 'fork_existing'),
    ('`cloudflare_tunnel_name`, and Cloudflare tunnel token', 'side-by-side shared tunnel guidance', 'fork_existing'),
    ("Add this fork's `public_hostname` to the existing Cloudflare tunnel", 'second-fork Cloudflare hostname step', 'fork_existing'),
    ('open the existing tunnel and add a public hostname with these values', 'second-fork existing tunnel guidance', 'fork_existing'),
    ('`app_name`', 'side-by-side app identity field listed for non-reuse', 'fork_existing'),
    ('LOCALCLUSTER_RUNNER_LABEL', 'side-by-side runner label variable guidance', 'settings'),
    ('Repository -> Settings -> Secrets and variables -> Actions -> Variables', 'GitHub repository variables UI path', 'settings'),
    ('No GitHub token goes into the vault.', 'no stored registry token guidance', 'release_contract'),
    ('only `read:packages`', 'minimum registry permission for optional manual-deploy tokens', 'release_contract'),
    ('Name: ANSIBLE_VAULT_PASSWORD', 'manual GitHub vault secret guidance', 'settings'),
    ('This secret is the Ansible Vault password.', 'vault secret purpose', 'settings'),
    ('release-manifest.json', 'release manifest explanation', 'release_contract'),
    ('### Runner And Docker Storage Maintenance', 'maintenance workflow guidance', 'operations'),
    ('### Deployment lock', 'deployment lock recovery guidance', 'entry'),
    ('### Tool provisioning: --check versus --provision', 'check-only versus provisioning guidance', 'operations'),
    ('Runner policy:', 'self-hosted runner policy', 'operations'),
    ('summary.sh', 'deployment summary command guidance', 'operations'),
    ('doctor.sh', 'doctor readiness command guidance', 'operations'),
    ('acceptance-check.sh', 'acceptance check guidance', 'operations'),
    ('report-nodes.sh', 'node report guidance', 'operations'),
    ('list-deployed-apps.sh', 'deployed app marker listing guidance', 'fork_existing'),
    ('validate-side-by-side.sh', 'side-by-side marker validation guidance', 'fork_existing'),
    ('verify-backup.sh', 'backup verification guidance', 'operations'),
    ('check-github-runner.sh', 'GitHub runner API check guidance', 'operations'),
    ('check-cloudflare-tunnel.sh', 'Cloudflare read-only check guidance', 'operations'),
]:
    owner_path = CLUSTER_ENTRY if owner == "entry" else DOC_OWNER_PATHS[owner]
    if needle == "`app_name`":
        error = missing_section_literal(
            cluster_guide_documents,
            CLUSTER_ENTRY,
            owner_path,
            "For a second fork on the same nodes, do not reuse these values from the first app",
            "The second fork normally reuses the same machine IPs",
            needle,
            why,
        )
    else:
        error = missing_literal(cluster_guide_documents, CLUSTER_ENTRY, owner_path, needle, why)
    if error:
        fail(error)
for document_path, document_text in cluster_guide_documents.items():
    if "gh repo clone Grumlebob/BlazorAutoApp" in document_text:
        fail(f"{document_path}: clone commands must be fork-safe, not hardcoded to the original repository")

for document_path, document_text in cluster_guide_documents.items():
    for line_number, line in enumerate(document_text.splitlines(), start=1):
        if 'ansible ' in line and '-a "cd ' in line and "-m ansible.builtin.shell" not in line:
            fail(
                f"{document_path}:{line_number}: ansible commands using cd/&& must use -m ansible.builtin.shell"
            )


tracked = tracked_files()
text_suffixes = {".cs", ".csproj", ".props", ".targets", ".json", ".yml", ".yaml", ".md", ".ps1", ".cmd", ".sh"}
text_names = {"Dockerfile", "docker-compose.yml", ".env.example", "global.json"}
for path in sorted(tracked):
    if path.startswith("docs/plans/archive/") or path == "CarefulUpgradeReview.md":
        continue
    file_path = Path(path)
    if file_path.suffix not in text_suffixes and file_path.name not in text_names:
        continue
    text = read(path)
    for stale in [
        "postgres:16" + ".14-alpine3.23",
        "redis:7" + ".4.9-alpine3.21",
        "testcontainers/ryuk:0" + ".12.0",
        "actions/download-artifact@" + "v4",
        "rhysd/actionlint:1" + ".7.7",
        "docker/dockerfile:1" + ".7-labs",
    ]:
        if stale in text:
            fail(f"{path}: stale runtime/tooling pin remains: {stale}")

for path in [
    ".env",
    "secrets.env",
    "Deployment/LocalCluster/machines.yml",
    "Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml",
]:
    if path in tracked:
        fail(f"local or secret file must not be tracked: {path}")

vault_path = ROOT / "Deployment/LocalCluster/inventory/prod/vault.yml"
if vault_path.exists():
    first_line = vault_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[0:1]
    if not first_line or not first_line[0].startswith("$ANSIBLE_VAULT;"):
        fail("Deployment/LocalCluster/inventory/prod/vault.yml exists but is not Ansible Vault encrypted")

for path in tracked:
    if re.search(r"(^|/)(__pycache__|\.pytest_cache)(/|$)", path) or re.search(
        r"\.(pyc|pyo|pyd|pfx|tmp|log)$", path
    ):
        fail(f"generated/cache/secret-like file must not be tracked: {path}")

for path in sorted(tracked):
    if not path.startswith("Deployment/LocalCluster/Scripts/") or not path.endswith(".sh"):
        continue
    text = read(path)
    if "REPO_ROOT=" not in text:
        continue
    if path.startswith("Deployment/LocalCluster/Scripts/Component/node-db/"):
        continue
    elif path.startswith("Deployment/LocalCluster/Scripts/Component/"):
        if "../../../.." not in text:
            fail(f"{path}: Component scripts must go up four levels from Scripts/Component to repo root")
    else:
        if "../../.." not in text:
            fail(f"{path}: top-level Scripts commands must go up three levels from Scripts to repo root")

for script_path in sorted((ROOT / "Deployment/LocalCluster/Scripts").rglob("*.sh")):
    rel_script = script_path.relative_to(ROOT).as_posix()
    text = read(rel_script)
    script_dir = script_path.parent
    scripts_dir = script_dir.parent if script_dir.name == "Component" else script_dir
    for variable, base_dir in [("SCRIPT_DIR", script_dir), ("SCRIPTS_DIR", scripts_dir)]:
        for match in re.finditer(r"\$" + variable + r"/([A-Za-z0-9_./-]+\.sh)", text):
            rel_target = match.group(1)
            target = (base_dir / rel_target).resolve()
            if not target.exists():
                fail(f"{rel_script}: references missing ${variable}/{rel_target}")


for path in deployment_text_files():
    rel = path.relative_to(ROOT).as_posix()
    if rel == "Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py":
        continue
    text = path.read_text(encoding="utf-8-sig")
    for stale, replacement in [
        ("improveddb", "books"),
        ("/opt/improveddb", "/opt/books"),
        ("node-db-redis", "node-db"),
        ("NODE_DB_REDIS", "NODE_DB"),
        ("db_redis", "node_db"),
        ("db-redis", "node-db"),
    ]:
        if stale in text:
            fail(f"{rel}: stale deployment identifier {stale}; use {replacement}")
    if "releases/latest" in text:
        fail(f"{rel}: deployment must not install from latest release URLs")
    if "DEPLOY_SSH_KEY" in text or "SHIP_DEPLOY_KEY" in text:
        fail(f"{rel}: deploy SSH key path must be derived from app_name, not local overrides")
    if "sudo apt install -y ansible" in text or "sudo apt-get install -y ansible" in text:
        fail(f"{rel}: use Deployment/LocalCluster/Scripts/install-ansible.sh instead of distro Ansible")
    if "ansible.builtin.apt_repository" in text:
        fail(f"{rel}: use ansible.builtin.deb822_repository instead of deprecated apt_repository")
    if "ansible_architecture" in text or "ansible_date_time" in text:
        fail(f"{rel}: use ansible_facts[...] instead of deprecated top-level injected facts")
    for forbidden in [".deploy.local", "discover-node", "health-check"]:
        if forbidden in text:
            fail(f"{rel}: contains stale deployment reference: {forbidden}")
    for stale_setting in [
        "caddy_sticky_cookie_name",
        "caddy_bind_address",
        "caddy_http_port",
    ]:
        if stale_setting in text:
            fail(f"{rel}: contains stale deployment setting: {stale_setting}")
    for old_prefix in [
        "Deployment/LocalCluster/scripts",
        "../scripts",
        "../../scripts",
        "Deployment/scripts",
        "Deployment/ansible",
        "Deployment/inventory",
        "Deployment/compose",
        "Deployment/caddy",
        "Deployment/machines",
    ]:
        if old_prefix in text:
            fail(f"{rel}: contains old deployment layout reference: {old_prefix}")


all_vars = read("Deployment/LocalCluster/inventory/prod/group_vars/all.yml")
all_var_keys = re.findall(r"^([A-Za-z_][A-Za-z0-9_]*):", all_vars, re.MULTILINE)
for release_key in ["app_image", "migration_bundle_name", "migration_runtime", "migration_artifact_name"]:
    if release_key in all_var_keys:
        fail(
            "Deployment/LocalCluster/inventory/prod/group_vars/all.yml: "
            f"{release_key} belongs in Deployment/Common/release.yml"
        )
for key in all_var_keys:
    error = missing_literal(
        cluster_guide_documents,
        CLUSTER_ENTRY,
        DOC_OWNER_PATHS["settings"],
        f"`{key}`",
        f"all.yml setting documentation: {key}",
    )
    if error:
        fail(error)

try:
    common_validation = subprocess.run(
        [sys.executable, str(ROOT / "Deployment/Common/Scripts/Component/lib/validate-common-release.py")],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
except OSError as exc:
    fail(f"unable to run common release validation: {exc}")
else:
    if common_validation.returncode != 0:
        fail("Deployment/Common/release.yml failed validation: " + (common_validation.stderr or common_validation.stdout).strip())

try:
    settings_validation = subprocess.run(
        [sys.executable, str(ROOT / "Deployment/LocalCluster/Scripts/Component/lib/validate-deploy-settings.py")],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
except OSError as exc:
    fail(f"unable to run deployment settings validation: {exc}")
else:
    if settings_validation.returncode != 0:
        fail(
            "Deployment/LocalCluster/inventory/prod/group_vars/all.yml failed validation: "
            + (settings_validation.stderr or settings_validation.stdout).strip()
        )
cloudflared_match = re.search(r"^cloudflared_version:\s*(\S+)\s*$", all_vars, re.MULTILINE)
if not cloudflared_match:
    fail("Deployment/LocalCluster/inventory/prod/group_vars/all.yml: missing cloudflared_version")
elif cloudflared_match.group(1) == "latest":
    fail("cloudflared_version must be pinned, not latest")

require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_version != \"latest\"",
    "cloudflared pinned-version guard",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared --version",
    "cloudflared installed-version verification",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "path: /etc/cloudflared",
    "cloudflared config directory creation",
)

require_contains(
    "Deployment/LocalCluster/ansible/playbooks/site.yml",
    "../../../Common/release.yml",
    "shared release vars file loaded by LocalCluster playbook",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "This deployment supports only x86_64/amd64 Linux machines.",
    "amd64-only cloudflared guard",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared-linux-amd64.deb",
    "amd64 cloudflared package",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "tunnel-token.sha256",
    "Cloudflare tunnel token change marker",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_tunnel_token_marker_missing",
    "Cloudflare missing marker recovery",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "Compute Cloudflare tunnel token hash",
    "Cloudflare token hash computed before dependent facts",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_tunnel_token_hash_mismatch",
    "Cloudflare token mismatch detection",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_tunnel_token_changed | bool",
    "Cloudflare token change condition coerced to bool",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared service uninstall",
    "Cloudflare tunnel token rotation handling",
)
require_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_allow_token_rotation",
    "side-by-side-safe Cloudflare tunnel token replacement guard",
)
require_not_contains(
    "Deployment/Common/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_deb_arch",
    "cloudflared multi-architecture package mapping",
)
cloudflared_tasks = read("Deployment/Common/ansible/roles/cloudflared/tasks/main.yml")
cloudflared_refuse_match = re.search(
    r"- name: Refuse accidental Cloudflare tunnel token replacement[\s\S]+?(?=\n- name:)",
    cloudflared_tasks,
)
if cloudflared_refuse_match and "cloudflared_tunnel_token_changed" in cloudflared_refuse_match.group(0):
    fail("Deployment/Common/ansible/roles/cloudflared/tasks/main.yml: missing marker must recover, only hash mismatch should refuse token replacement")


ansible_cfg = read("Deployment/LocalCluster/ansible/ansible.cfg")
for needle, why in [
    ("inventory = ../inventory/prod/hosts.yml", "default production inventory"),
    ("roles_path = roles:../../Common/ansible/roles", "local and Common roles path"),
    ("interpreter_python = auto_silent", "Python interpreter auto-detection"),
]:
    if needle not in ansible_cfg:
        fail(f"Deployment/LocalCluster/ansible/ansible.cfg: missing {why}")


hosts = read("Deployment/LocalCluster/inventory/prod/hosts.yml")
for needle, why in [
    ("load_balancer:", "load balancer group"),
    ("app_servers:", "app server group"),
    ("node_db:", "database node group"),
    ("node-main:", "node-main host"),
    ("node-app1:", "node-app1 host"),
    ("node-app2:", "node-app2 host"),
    ("node-db:", "node-db host"),
    ("ansible_python_interpreter: /usr/bin/python3", "stable Python interpreter path"),
]:
    if needle not in hosts:
        fail(f"Deployment/LocalCluster/inventory/prod/hosts.yml: missing {why}")
generate_inventory = read("Deployment/LocalCluster/Scripts/Component/lib/generate-inventory.py")
for needle, why in [
    ("REQUIRED_NODES = [\"node-main\", \"node-app1\", \"node-app2\", \"node-db\"]", "required node list"),
    ("import ipaddress", "strict IP address validation"),
    ("load_settings", "shared deployment settings reader"),
    ("unexpected node", "unexpected node rejection"),
    ("duplicate IP address", "duplicate IP rejection"),
    ("duplicate MAC address", "duplicate MAC rejection"),
    ("node_db:", "node_db inventory group rendering"),
    ("render_bootstrap_hosts", "bootstrap inventory rendering"),
    ("install_user", "install user support"),
    ("ansible_python_interpreter: /usr/bin/python3", "stable Python interpreter rendering"),
    ("--check", "read-only machines.yml validation mode"),
    ("machines.yml is valid", "clear machines validation success line"),
]:
    if needle not in generate_inventory:
        fail(f"Deployment/LocalCluster/Scripts/Component/lib/generate-inventory.py: missing {why}")
if "def read_simple_group_var" in generate_inventory:
    fail("Deployment/LocalCluster/Scripts/Component/lib/generate-inventory.py: use deploy_settings.py instead of a local all.yml parser")

for path, checks in {
    "Deployment/LocalCluster/Scripts/Component/lib/read-deploy-setting.py": [
        ("load_settings", "shared deployment settings reader"),
        ("load_settings(settings_path, validate_file=True)", "settings validation before read"),
    ],
    "Deployment/LocalCluster/Scripts/Component/lib/validate-deploy-settings.py": [
        ("load_settings", "shared deployment settings validator"),
    ],
    "Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py": [
        ("REQUIRED_KEYS", "required all.yml keys"),
        ("from simple_yaml import read_simple_yaml", "Common simple YAML parser reuse"),
        ("OPTIONAL_KEYS", "derived optional settings"),
        ("postgres_port", "configurable PostgreSQL host port"),
        ("redis_port", "configurable Redis host port"),
        ("runner_label", "derived app-specific runner label"),
        ("def apply_defaults", "derived settings defaults"),
        ("def load_settings", "shared settings loader"),
        ("def validate", "shared settings validator"),
    ],
}.items():
    text = read(path)
    for needle, why in checks:
        if needle not in text:
            fail(f"{path}: missing {why}")


# Deployments use Docker, but published demo logins must never be seeded there.
for seeded_path in [
    "Deployment/LocalCluster/compose/app-server/docker-compose.yml",
    "Deployment/Cloud/compose/app-server/docker-compose.yml",
]:
    if 'LocalAccounts__Enabled: "false"' not in read(seeded_path):
        fail(f'{seeded_path}: missing LocalAccounts__Enabled: "false" (no seeded demo logins in deployments)')

ci_provenance = read("Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py")
for needle in ['ALLOWED_EVENTS = {"push", "workflow_dispatch"}', "verify_publishing_job", "/attempts/{attempt}/jobs", 'job.get("run_attempt")', 'job.get("head_sha")']:
    if needle not in ci_provenance:
        fail(f"CI release provenance: missing publishing verification contract {needle}")
release_settings_source = read("Deployment/Common/Scripts/Component/lib/release_settings.py")
for needle in ("PAYLOAD_PREFIX_RE", "def derive_release_payload_image(app_image: str, prefix: str = \"\")", "validate_release_payload_image"):
    if needle not in release_settings_source:
        fail(f"CI release package settings: missing validated payload-prefix support {needle}")
if "release_payload_prefix: private-" not in read("Deployment/Common/release.yml"):
    fail("Deployment/Common/release.yml: final payload packages must use the prepared private package prefix")

deploy_app_compose = read("Deployment/LocalCluster/compose/app-server/docker-compose.yml")
for needle, why in [
    ("image: ${APP_IMAGE_REF:?APP_IMAGE_REF is required}", "exact release image reference"),
    ("ASPNETCORE_HTTP_PORTS: ${APP_PORT}", "configured app listen port"),
    ('"${APP_PORT}:${APP_PORT}"', "configured published app port"),
    ('Database__RunMigrationsAtStartup: "false"', "production startup migrations disabled"),
    ("ConnectionStrings__DefaultConnection", "database connection injection"),
    ("Port=${POSTGRES_PORT}", "configurable PostgreSQL port injection"),
    ("Redis__Configuration", "Redis configuration injection"),
    ("${REDIS_HOST}:${REDIS_PORT}", "configurable Redis port injection"),
]:
    if needle not in deploy_app_compose:
        fail(f"Deployment/LocalCluster/compose/app-server/docker-compose.yml: missing {why}")
for local_only in ["redisinsight", "datalust/seq", "build:"]:
    if local_only in deploy_app_compose:
        fail(f"Deployment/LocalCluster/compose/app-server/docker-compose.yml: contains local-only deployment content: {local_only}")

node_db_compose = read("Deployment/LocalCluster/compose/node-db/docker-compose.yml")
for needle, why in [
    ("postgres:", "PostgreSQL service"),
    ("redis:", "Redis service"),
    ("POSTGRES_PASSWORD", "PostgreSQL secret injection"),
    ('"${POSTGRES_PORT}:5432"', "configurable PostgreSQL host port"),
    ("REDIS_PASSWORD", "Redis secret injection"),
    ('"${REDIS_PORT}:6379"', "configurable Redis host port"),
]:
    if needle not in node_db_compose:
        fail(f"Deployment/LocalCluster/compose/node-db/docker-compose.yml: missing {why}")
for service, image in [("PostgreSQL", "postgres"), ("Redis", "redis")]:
    image_match = re.search(rf"^\s*image:\s*{image}:([^\s]+)\s*$", node_db_compose, re.MULTILINE)
    if not image_match:
        fail(f"Deployment/LocalCluster/compose/node-db/docker-compose.yml: missing {service} image tag")
        continue
    tag = image_match.group(1)
    if not re.match(r"^\d+(?:\.\d+){1,2}-alpine\d+\.\d+$", tag):
        fail(f"Deployment/LocalCluster/compose/node-db/docker-compose.yml: {service} image tag must pin an exact version and Alpine release")
for moving_image in ["postgres:18-alpine", "redis:8-alpine", "postgres:latest", "redis:latest"]:
    if moving_image in node_db_compose:
        fail(f"Deployment/LocalCluster/compose/node-db/docker-compose.yml: use exact image tags, not {moving_image}")
for needle, why in [
    ("postgres:18.4-alpine3.23", "PostgreSQL 18 pinned image"),
    ("redis:8.8.0-alpine3.23", "Redis 8 pinned image"),
    ("postgres_data:/var/lib/postgresql", "PostgreSQL 18 volume root mount"),
    ("REDISCLI_AUTH=${REDIS_PASSWORD}", "Redis health check uses environment authentication"),
]:
    if needle not in node_db_compose:
        fail(f"Deployment/LocalCluster/compose/node-db/docker-compose.yml: missing {why}")


for path, needle, why in [
    (
        "BlazorAutoApp/Infrastructure/Hosting/AppCachingExtensions.cs",
        "PersistKeysToStackExchangeRedis",
        "Redis-backed Data Protection",
    ),
    ("BlazorAutoApp/Program.cs", "UseForwardedHeaders", "forwarded header middleware"),
    (
        "BlazorAutoApp/Infrastructure/Hosting/HealthCheckEndpointExtensions.cs",
        "MapHealthChecks(\"/health/live\"",
        "liveness health endpoint",
    ),
    (
        "BlazorAutoApp/Infrastructure/Hosting/HealthCheckEndpointExtensions.cs",
        "MapHealthChecks(\"/health/ready\"",
        "readiness health endpoint",
    ),
    (
        "BlazorAutoApp/Infrastructure/Persistence/PersistenceExtensions.cs",
        "Database:RunMigrationsAtStartup",
        "migration startup guard",
    ),
]:
    if needle not in read(path):
        fail(f"{path}: missing {why}")
require_contains(
    "BlazorAutoApp/BlazorAutoApp.csproj",
    "Microsoft.AspNetCore.DataProtection.StackExchangeRedis",
    "Redis Data Protection package",
)

require_contains(
    "Deployment/Common/Scripts/install-ansible.sh",
    "sshpass",
    "sshpass for Ansible password bootstrap",
)
require_contains(
    "Deployment/Common/Scripts/install-ansible.sh",
    "already installed",
    "idempotent Ansible install skip",
)
require_contains(
    "Deployment/LocalCluster/Scripts/install-ansible.sh",
    "Deployment/Common/Scripts/install-ansible.sh",
    "LocalCluster Ansible installer wrapper points to Common",
)
# CI/CD jobs only check prerequisites. apt runs during explicit provisioning,
# because a host-wide apt lock (for example mint-refresh-ca) breaks CI otherwise.
for script, needle in [
    ("Deployment/Common/Scripts/install-ansible.sh", '--check) MODE="check"'),
    ("Deployment/Common/Scripts/ensure-actions-runner-prereqs.sh", '--check) MODE="check"'),
]:
    require_contains(script, needle, "check-only mode without apt or sudo")
require_contains(".github/workflows/ci.yml", "ensure-actions-runner-prereqs.sh --check", "check-only runner prerequisites in CI")
require_contains(".github/workflows/ci.yml", "Tests/test-install-ansible-check.sh", "Ansible check-only setup test")
for workflow, installer in [
    (".github/workflows/cd-localcluster.yml", "Deployment/LocalCluster/Scripts/install-ansible.sh --check"),
    (".github/workflows/cd-cloud.yml", "Deployment/Common/Scripts/install-ansible.sh --check"),
]:
    require_contains(workflow, installer, "check-only Ansible activation in CD")
require_contains(
    "Deployment/LocalCluster/Scripts/setup-control-machine.sh",
    "validate-deploy-settings.sh",
    "deployment settings validation before control setup",
)
require_contains(
    "Deployment/Common/ansible/roles/caddy_install/tasks/main.yml",
    "https://github.com/caddyserver/caddy/releases/download/v{{ caddy_package_version }}",
    "pinned official Caddy release package",
)
require_contains(
    "Deployment/Common/ansible/roles/caddy_install/tasks/main.yml",
    "checksum: \"sha256:{{ caddy_package_sha256[caddy_package_architectures[ansible_facts['architecture']]] }}\"",
    "verified Caddy package download",
)
for role in ("caddy_install", "mint_base", "docker"):
    require_contains(
        f"Deployment/Common/ansible/roles/{role}/tasks/main.yml",
        "../../../Scripts/retire-caddy-cloudsmith-source.py",
        "retire only the known legacy Caddy source before apt",
    )
bootstrap_source = read("Deployment/LocalSingleNode/Scripts/lib/bootstrap.py")
retirement_position = bootstrap_source.find("retire-caddy-cloudsmith-source.py")
if retirement_position < 0 or retirement_position > bootstrap_source.find('for action in (["update"]'):
    fail("LocalSingleNode bootstrap must retire the legacy Caddy source before apt")
require_contains("Deployment/LocalSingleNode/Scripts/lib/bootstrap.py", '"timeout", "--foreground", "600", "apt-get"', "foreground apt timeout without terminal job-control stops")
require_contains("Deployment/LocalSingleNode/Scripts/lib/bootstrap.py", "stdin=subprocess.DEVNULL", "noninteractive bootstrap apt input")
require_contains(
    "Deployment/LocalCluster/ansible/roles/caddy/tasks/main.yml",
    "Reload Caddy with validated configuration",
    "partial-failure-safe Caddy reload",
)

for needle, why in [
    ("could not detect this node's LAN IP address", "clear LAN IP detection failure"),
    ("could not detect the MAC address", "clear LAN MAC detection failure"),
]:
    if needle not in read("Deployment/LocalCluster/Scripts/bootstrap-node.sh"):
        fail(f"Deployment/LocalCluster/Scripts/bootstrap-node.sh: missing {why}")
    if needle not in read("Deployment/LocalCluster/Scripts/discover-machines.sh"):
        fail(f"Deployment/LocalCluster/Scripts/discover-machines.sh: missing {why}")


ci = read(".github/workflows/ci.yml")
for needle, why in [
    ("github.event.pull_request.head.repo.full_name == github.repository", "external-fork pull request guard before self-hosted runner allocation"),
    ("localcluster-books", "app-specific self-hosted runner label fallback"),
    ("Verify CI runner", "explicit CI runner verification"),
    ("Ensure self-hosted runner prerequisites", "node-main prerequisite bootstrap step"),
    ("RUNNER_TEMP", "temporary self-hosted runner tool install directories"),
    ("find Deployment/LocalSingleNode/Scripts Deployment/LocalCluster/Scripts Deployment/Common/Scripts -type f -name '*.sh'", "LocalCluster and Common shell lint roots"),
    ("find Deployment/Cloud/Scripts -type f -name '*.sh'", "Cloud shell lint root"),
    ("bash Deployment/Common/Scripts/validate-common-release.sh", "common release validation step"),
    ("bash Deployment/Cloud/Scripts/validate-cloud-settings.sh", "Cloud settings validation step"),
    ("bash Deployment/LocalCluster/Scripts/audit-deployment.sh", "deployment audit step"),
    ("bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh", "rendered deployment template validation step"),
    ("python -m pip install --constraint \"$CI_PYTHON_CONSTRAINTS\" yamllint", "pinned deployment lint tool install"),
    ("python -m pip install --constraint \"$CI_PYTHON_CONSTRAINTS\" jinja2", "pinned template render tool install"),
    ("CI_PYTHON_CONSTRAINTS", "pinned Python CI dependency path"),
    ("PIP_CONSTRAINT", "bounded pip dependency resolution"),
    ("pip==26.2.1", "pinned pip bootstrap"),
    ("yamllint .github Deployment docker-compose.yml .yamllint.yml", "deployment YAML lint step"),
    ("bash Scripts/CI/run-actionlint.sh", "pinned queue-aware actionlint runner"),
    ("node-version: 24.21.0", "React Node.js version pinned to its declared toolchain"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh app_image", "shared release image setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_bundle_name", "shared migration bundle setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_runtime", "shared migration runtime setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh release_payload_prefix", "configured GHCR release payload package prefix"),
    ("Build and test both frontend profiles", "both-profile .NET validation gate"),
    ("bash Scripts/CI/validate-frontend-profiles.sh", "sequential build and test of both frontend profiles"),
    ("Test required .NET test-result counts", "strict .NET result parser unit tests"),
    ("python3 -m unittest Scripts/CI/tests/test_validate_dotnet_test_results.py -v", "strict .NET test result count validator tests"),
    ('--expected-skipped 0 --suite "Testcontainers lifecycle"', "Testcontainers lifecycle rejects skipped tests"),
    ("Validate local Compose frontend profiles", "local Compose target validation for both profiles"),
    ("Install pinned npm for React frontend", "pinned React npm is installed in runner temporary storage"),
    ('npm_prefix="$RUNNER_TEMP/react-npm-12.2.0"', "React npm install uses an isolated temporary prefix"),
    ('echo "$npm_prefix/bin" >> "$GITHUB_PATH"', "pinned React npm is used by subsequent CI steps"),
    ('test "$(npm --version)" = "12.2.0"', "CI verifies the exact React npm version"),
    ("Install React frontend dependencies", "locked React frontend dependency install"),
    ("Audit React frontend dependencies", "React frontend dependency audit"),
    ("Check React OpenAPI contract", "generated React OpenAPI contract validation"),
    ("Lint React frontend", "React frontend lint validation"),
    ("Test React frontend", "React unit tests that must all pass without skips"),
    ("report.numPassedTests !== report.numTotalTests", "React unit tests must all pass"),
    ("report.numPendingTests !== 0", "React unit tests must not pass with skips"),
    ("Build React frontend", "React frontend production build"),
    ("dotnet ef migrations bundle", "migration bundle build"),
    ('--runtime "${MIGRATION_RUNTIME}"', "shared migration runtime usage"),
    ("docker build", "Docker image build"),
    ("--pull", "Docker build base image freshness"),
    ("postgres:18.4-alpine3.23", "PostgreSQL 18 integration test image pre-pull"),
    ("redis:8.8.0-alpine3.23", "Redis 8 integration test image pre-pull"),
    ("needs.validate.result == 'success'", "main publisher requires successful full validation"),
    ("Store CI reports on this runner", "bounded runner-local test report storage"),
    ("REPORT_STATUS: ${{ job.status }}", "report retention follows exact terminal job status"),
    ("--job validate", "validation reports use a distinct store identity"),
    ("--job publish-main", "publisher reports use a distinct store identity"),
    ("Scripts/CI/tests/test_ci_report_store.py", "runner-local report store tests"),
    ("Remove this run's local Docker image", "owned CI image cleanup step"),
    ("bash Deployment/LocalCluster/Scripts/ci-docker-smoke.sh --cleanup-only", "interrupted-run smoke cleanup"),
    ("always() && steps.ci_smoke.outcome != 'skipped'", "always-run interrupted smoke cleanup guard"),
    ('docker image rm "${APP_IMAGE}:${image_tag}"', "exact profile-tag CI image removal"),
    ('image_tag="${CI_IMAGE_TAG}-${profile}"', "separate exact image tag for each frontend profile"),
    ('ci_image_tag="${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"', "per-run CI image tag"),
    ("bash Scripts/CI/check-runner-capacity.sh", "report-only runner capacity check"),
    ("bash Deployment/LocalCluster/Scripts/ci-docker-smoke.sh", "Docker and browser smoke"),
    ("bash Deployment/LocalCluster/Scripts/Tests/test-ci-docker-smoke.sh", "Docker smoke resource lifecycle test"),
    ("python3 -m unittest Scripts/CI/tests/test_frontend_profile.py", "frontend profile resolver and MSBuild validation tests"),
    ("python3 -m unittest Scripts/CI/tests/test_deployed_site_acceptance.py -v", "trusted profile split and read-only React HTTP acceptance tests"),
    ("python3 Scripts/Frontend/resolve_frontend_profile.py", "single validated frontend profile resolver"),
    ("frontend_profile: ${{ steps.frontend_profile.outputs.profile }}", "validated profile passed from CI validation to release"),
    ("-p:FrontendProfile=${RESOLVED_FRONTEND_PROFILE}", "resolved frontend profile passed to MSBuild"),
    ('--build-arg "FRONTEND_PROFILE_OVERRIDE=${RESOLVED_FRONTEND_PROFILE}"', "resolved frontend profile passed to Docker builds"),
    ('--target "${docker_target}"', "selected profile Docker target passed to image build"),
    ("BlazorAuto) docker_target=final-blazor ;;", "Blazor profile selects its isolated image target"),
    ("React) docker_target=final-react ;;", "React profile selects its isolated image target"),
    ("needs.validate.outputs.frontend_profile", "main release uses the validated profile"),
    ("python3 -m unittest Scripts/CI/tests/test_migration_staging_artifact.py", "migration staging provenance tests"),
    ("Deployment/Common/Scripts/Tests/test_release_contract.py", "release manifest contract tests"),
    ("Deployment/Common/Scripts/Tests/test_ci_provenance.py", "CI provenance selection tests"),
    ("Deployment/Common/Scripts/Tests/test_target_gate.py", "exact deployment target gate fixtures"),
    ("bash Deployment/LocalCluster/Scripts/Tests/test-verify-release-identity.sh", "release identity fixture test"),
    ("bash Deployment/LocalSingleNode/Scripts/Tests/test-verify-release-identity.sh", "single-node release identity fixture test"),
    ("bash Deployment/LocalCluster/Scripts/Tests/test-localcluster-maintenance.sh", "maintenance fixture test"),
    ("bash Deployment/LocalCluster/Scripts/Tests/test-prune-docker-residue-low-disk.sh", "Docker cleanup fixture test"),
    ("bash Deployment/Common/Scripts/Tests/test-prune-actions-runner-residue.sh", "runner residue fixture test"),
    ("python3 Deployment/LocalCluster/Scripts/Tests/test_prune_ci_residue.py", "CI residue safeguard tests"),
    ("python3 Deployment/LocalCluster/Scripts/Tests/test_runner_identity.py", "runner identity fixtures"),
    ("python3 -m unittest Deployment/LocalCluster/Scripts/Tests/test_doc_slice_loader.py -v", "bounded documentation slice loader tests"),
    ("python3 -m unittest Deployment/LocalCluster/Scripts/Tests/test_read_live_release_ci_run_ids.py -v", "live release identity protection tests"),
    ("Deployment/Common/Scripts/Tests/test_release_status.py", "shared release status validation tests"),
    ("python3 -m unittest Deployment/LocalCluster/Scripts/Tests/test_release_status.py -v", "LocalCluster read-only release status tests"),
    ("python3 -m unittest Deployment/LocalSingleNode/Scripts/Tests/test_release_status.py -v", "LocalSingleNode read-only release status tests"),
    ("python3 -m unittest discover -s Deployment/LocalSingleNode/Scripts/Tests -v", "single-node and deployed release acceptance tests"),
    ("Deployment/Common/Scripts/Tests/test_prune_actions_artifacts.py", "artifact retention tests"),
    ("RUN_TESTCONTAINER_LIFECYCLE: \"1\"", "Testcontainers lifecycle proof"),
    ("global-json-file: global.json", "SDK pinned by global.json"),
    ("ansible-playbook", "LocalCluster playbook syntax check"),
    ("--syntax-check", "LocalCluster playbook syntax check"),
    ("bash Deployment/Common/Scripts/Tests/test-with-deploy-lock.sh", "deployment lock behaviour tests"),
    ("docker push \"${APP_IMAGE}:${GITHUB_SHA}\"", "immutable configured image push"),
]:
    if needle not in ci:
        fail(f".github/workflows/ci.yml: missing {why}")
for pin in ("--expected-passed", "expectedTestCount"):
    if pin in ci:
        fail(f".github/workflows/ci.yml: test suites must not pin an exact pass count ({pin})")

profile_gate = read("Scripts/CI/validate-frontend-profiles.sh")
for needle, why in [
    ("validate_dotnet_test_results.py", "both profile suites validate their TRX results"),
    ("--filter 'FrontendProfile!=BlazorAuto'", "React excludes only tests explicitly restricted to Blazor Auto"),
    ("account_filter='FullyQualifiedName~Features.Login.Accounts'", "both profiles run the account integration tests explicitly"),
    ("account_filter+='&FrontendProfile!=BlazorAuto'", "React excludes only account tests tagged for Blazor Auto"),
    ('--filter "$account_filter"', "account integration gate uses its profile-aware filter"),
    ("--expected-skipped 0", "account integration tests cannot silently skip"),
    ('--suite "$profile account integration tests"', "account integration results have a distinct required suite label"),
]:
    if needle not in profile_gate:
        fail(f"Scripts/CI/validate-frontend-profiles.sh: missing {why}: {needle}")
if any(pin in profile_gate for pin in ("expected_passed", "--expected-passed")) or re.search(r"--expected-skipped(?!\s+0)", profile_gate):
    fail("Scripts/CI/validate-frontend-profiles.sh: profile suites must not pin test counts; "
         "the validator rejects failures and skips that are not explicit opt-ins; only the account suite pins zero skips")

dockerfile = read("BlazorAutoApp/Dockerfile")
for needle, why in [
    ("FROM node:24.21.0-bookworm-slim AS react-dependencies", "pinned Node toolchain is isolated in React dependency stage"),
    ("npm install --global npm@12.2.0 && npm ci", "pinned npm install from the React lockfile"),
    ("FROM react-dependencies AS react-assets", "React asset build reuses its isolated dependency stage"),
    ("npm run build && test -s build/client/index.html", "React build must produce its shell"),
    ("COPY Directory.Build.targets ./", "MSBuild profile validation target copied into Docker source"),
    ("COPY frontend-profile.txt ./", "tracked frontend profile copied into Docker source"),
    ("FROM source AS publish-blazor", "Blazor publish is isolated from Node assets"),
    ("FROM source AS publish-react", "React publish has its own selected asset stage"),
    ('test "$profile" = "BlazorAuto"', "Blazor target rejects a mismatched profile"),
    ('test "$profile" = "React"', "React target rejects a mismatched profile"),
    ("rm -rf ./BlazorAutoApp/Frontend/React/wwwroot", "React publish starts from a clean selected asset root"),
    ("test -s /tmp/react-client/index.html", "React publish fails when its bundle is missing"),
    ('"-p:FrontendProfile=$profile"', "same resolved profile passed to the selected Docker publish"),
    ("FROM base AS final-blazor", "Blazor final image target"),
    ("FROM base AS final-react", "React final image target"),
    ('ENTRYPOINT ["dotnet", "BlazorAutoApp.dll"]', "final images run the ASP.NET Core host"),
]:
    if needle not in dockerfile:
        fail(f"BlazorAutoApp/Dockerfile: missing {why}")

blazor_publish_stage = dockerfile.split("FROM source AS publish-blazor", 1)[1].split("FROM source AS publish-react", 1)[0]
if "react-assets" in blazor_publish_stage:
    fail("Blazor Docker target must not depend on the React npm stage")
if dockerfile.count("COPY --from=react-assets") != 1:
    fail("React bundle must be copied only into the React publish stage")
final_image_stages = dockerfile.split("FROM base AS final-blazor", 1)[1]
if "node:" in final_image_stages or "COPY --from=react-assets" in final_image_stages:
    fail("final runtime images must not copy Node or the Node build stage")

compose = read("docker-compose.yml")
for needle, why in [
    ("target: ${FRONTEND_DOCKER_TARGET:-final-blazor}", "Compose build target follows the selected profile"),
    ("FRONTEND_PROFILE_OVERRIDE: ${FRONTEND_PROFILE_OVERRIDE:-}", "Compose passes the resolved profile to Docker"),
]:
    if needle not in compose:
        fail(f"docker-compose.yml: missing {why}")

for path, checks in {
    ".yamllint.yml": [
        ("extends: default", "default yamllint rule base"),
        ("max-spaces-inside: 1", "YAML braces spacing rule"),
        ("min-spaces-from-content: 1", "YAML comments spacing rule"),
        ("comments-indentation: false", "YAML comment indentation tolerance"),
        ("line-length: disable", "long deployment command tolerance"),
        ("new-lines: disable", "Windows checkout line-ending tolerance"),
        ("forbid-explicit-octal: true", "explicit octal rule"),
        ("forbid-implicit-octal: true", "implicit octal rule"),
        ("truthy: disable", "GitHub Actions on-key tolerance"),
    ],
}.items():
    text = read(path)
    for needle, why in checks:
        if needle not in text:
            fail(f"{path}: missing {why}")
# node-main's Docker daemon is shared by every app on the cluster. CI may only
# remove resources it created; host-wide pruning belongs to reviewed maintenance.
for forbidden in ("prune-docker-residue.sh --force", "docker system prune", "docker container prune", "docker builder prune", "docker network prune", "docker volume prune"):
    if forbidden in ci:
        fail(f".github/workflows/ci.yml: CI must not run host-wide Docker cleanup: {forbidden}")
if ci.count("run: bash Deployment/LocalCluster/Scripts/ci-docker-smoke.sh --cleanup-only") != 2:
    fail(".github/workflows/ci.yml: both smoke jobs must recover their own interrupted resources")
if ci.index("ci-docker-smoke.sh --cleanup-only") > ci.index("name: Remove this run's local Docker image"):
    fail(".github/workflows/ci.yml: owned smoke resources must be removed before their exact image tag")
for needle in ("Cleanup-only requires the exact GitHub repository, run ID and attempt.", "expected_identity", "Owned smoke container remains", "Owned smoke network remains"):
    require_contains("Deployment/LocalCluster/Scripts/ci-docker-smoke.sh", needle, "exact-run interrupted cleanup and residue verification")
prune_script = read("Deployment/LocalCluster/Scripts/prune-docker-residue.sh")
for needle, why in [
    ("--include-unlabelled-host-residue", "explicit opt-in for host-wide prunes"),
    ("Docker volumes are protected", "volume protection statement"),
]:
    if needle not in prune_script:
        fail(f"Deployment/LocalCluster/Scripts/prune-docker-residue.sh: missing {why}")
if "docker volume prune" in prune_script or "system prune" in prune_script:
    fail("Deployment/LocalCluster/Scripts/prune-docker-residue.sh: must never prune volumes or the whole system")
if "${APP_IMAGE}:latest" in ci or "docker push \"${APP_IMAGE}:latest\"" in ci:
    fail(".github/workflows/ci.yml: CI must publish only immutable Git SHA image tags")
if "secrets.ANSIBLE_VAULT_PASSWORD" in ci:
    fail(".github/workflows/ci.yml: CI must not require the production Ansible Vault password")
if "ansible-lint" in ci or "ansible-vault encrypt" in ci:
    fail(".github/workflows/ci.yml: CI must not run dummy-vault Ansible linting")
if "cache: npm" in ci or "cache-dependency-path" in ci:
    fail(".github/workflows/ci.yml: CI must not use GitHub cloud npm cache on the self-hosted runner")
push_pos = ci.find('docker push "${APP_IMAGE}:${GITHUB_SHA}"')
manifest_pos = ci.find("Resolve pushed image digest and write release manifest")
receipt_pos = ci.find("Emit immutable release payload receipt")
if push_pos < 0 or manifest_pos < push_pos or receipt_pos < manifest_pos:
    fail(".github/workflows/ci.yml: GHCR payload receipt must follow the pushed image and verified manifest")
# Artifact retention runs daily on the maintenance runner, while host and
# Docker cleanup remain manual. Both selection/download and cleanup use the
# shared deployment lock and retain live, successful, and active release IDs.
maintenance = read(".github/workflows/localcluster-docker-maintenance.yml")
for needle, why in [
    ("workflow_dispatch:", "manual maintenance trigger"),
    ("artifact_only:", "manual artifact-only dispatch input"),
    ("default: false", "artifact-only dispatch preserves existing manual behavior by default"),
    ("schedule:", "daily artifact retention schedule"),
    ('cron: "17 3 * * *"', "daily artifact retention cron"),
    ("localcluster-books", "app-specific self-hosted runner label fallback"),
    ("bash Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh", "locked maintenance runner"),
    ("install-ansible.sh --check", "check-only Ansible activation"),
    ("prune-migration-artifacts:", "artifact retention job"),
    ("actions: write", "permission to prune old CI artifacts"),
    ("bash Deployment/Common/Scripts/with-deploy-lock.sh bash Deployment/LocalCluster/Scripts/prune-migration-artifacts.sh", "artifact selection and deletion under the shared lock"),
]:
    if needle not in maintenance:
        fail(f".github/workflows/localcluster-docker-maintenance.yml: missing {why}")
host_maintenance_job = maintenance.split("  prune:", 1)[-1].split("  prune-migration-artifacts:", 1)[0]
artifact_retention_job = maintenance.split("  prune-migration-artifacts:", 1)[-1]
dispatch_configuration = maintenance.split("  workflow_dispatch:", 1)[-1].split("  schedule:", 1)[0]
dispatch_expectations = [
    ("\n      artifact_only:\n", "artifact-only input declaration"),
    ("\n      apply_artifacts:\n", "manual artifact-apply input declaration"),
    ("\n        type: boolean\n", "boolean artifact-only input"),
    ("\n        default: false\n", "default-off artifact-only input"),
]
for needle, why in dispatch_expectations:
    if needle not in dispatch_configuration:
        fail(f".github/workflows/localcluster-docker-maintenance.yml: missing {why}")
if "if: github.event_name == 'workflow_dispatch' && inputs.artifact_only != true" not in host_maintenance_job:
    fail(".github/workflows/localcluster-docker-maintenance.yml: host or Docker cleanup must be skipped for artifact-only dispatches and schedules")
if "if: github.event_name == 'workflow_dispatch' || github.event.schedule == '17 3 * * *'" not in artifact_retention_job:
    fail(".github/workflows/localcluster-docker-maintenance.yml: manual and daily runs must run artifact retention")
if "ACTIONS_ARTIFACT_RETENTION_ENABLED: ${{ (github.event.schedule == '17 3 * * *' || (github.event_name == 'workflow_dispatch' && inputs.apply_artifacts == true)) && (vars.ACTIONS_ARTIFACT_RETENTION_ENABLED || 'false') }}" not in artifact_retention_job:
    fail(".github/workflows/localcluster-docker-maintenance.yml: manual artifact deletion must require apply_artifacts=true and the repository retention variable")
for needle, why in [
    ("Require main branch", "main-ref-only manual pruning"),
    ("Require green main CI for unchanged operation code", "verified operation source"),
    ("verify-operation-source.py", "green CI source gate"),
    ("ACTIONS_ARTIFACT_RETENTION_ENABLED", "default-off artifact deletion gate"),
]:
    if needle not in artifact_retention_job:
        fail(f".github/workflows/localcluster-docker-maintenance.yml: missing {why}")
prune_migration = read("Deployment/LocalCluster/Scripts/prune-migration-artifacts.sh")
for needle, why in [
    ("LOCALCLUSTER_DEPLOY_LOCK_TOKEN", "shared deployment lock ownership check"),
    ('--export-markers-dir "$marker_dir"', "pin retention uses verified remote release marker snapshots"),
    ('chmod 700 -- "$marker_dir"', "release marker snapshots use a private run-scoped directory"),
    ("trap cleanup_marker_snapshots EXIT", "release marker snapshots are removed after retention"),
    ('--current-marker "$marker_dir/release.json"', "current pin protection uses the remote marker snapshot"),
    ('--recovery-marker "$marker_dir/previous.json"', "recovery pin protection uses the remote marker snapshot"),
    ("read-live-release-ci-run-ids.py", "currently running CI release identity protection"),
    ("--protect-run-id", "deployed release artifacts are protected"),
    ("--keep 0", "retire unprotected legacy migration artifacts after the GHCR cutover"),
    ("--deployment-workflow-file cd-localcluster.yml", "active deployment protection"),
    ("--deployment-workflow-file cd-localsinglenode.yml", "single-node deployment protection for shared artifacts"),
    ("--max-unprotected-bytes 536870912", "fixed unprotected artifact cap"),
    ("--max-deletions 100", "bounded artifact deletion batch"),
    ("prune-actions-artifacts.sh", "shared exact-identity artifact pruning helper"),
]:
    if needle not in prune_migration:
        fail(f"Deployment/LocalCluster/Scripts/prune-migration-artifacts.sh: missing {why}")
if prune_migration.index("--export-markers-dir") > prune_migration.index('bash "$COMMON/prune-actions-artifacts.sh"'):
    fail("Deployment/LocalCluster/Scripts/prune-migration-artifacts.sh: verify remote release markers before artifact deletion")
cd_localcluster = read(".github/workflows/cd-localcluster.yml")
selection_download = workflow_step_text(cd_localcluster, "Select and retrieve the release payload under the shared lock")
for needle, why in [
    ("with-deploy-lock.sh", "release selection uses the shared deployment lock"),
    ("find-successful-ci-run.py", "receipt selector is invoked"),
    ('--target-sha "$TARGET_SHA"', "selector binds the requested target SHA"),
    ("--read-final-payload-receipt", "GHCR selection requires a run-bound final receipt"),
    ('--payload-app-image-prefix "$RELEASE_PAYLOAD_PREFIX"', "receipt selection uses the configured payload package prefix"),
    ("pull_release_payload.py", "GHCR payload is pulled and validated by digest"),
    ('--payload-image-prefix "$RELEASE_PAYLOAD_PREFIX"', "GHCR payload pull uses the configured package prefix"),
    ("pin_release_payload.py", "validated GHCR payload is retained as an offline local pin"),
    ("import_legacy_release_payload.py", "legacy artifact is selected by exact attempt and verified archive digest"),
    ('--root "${DEPLOY_ROOT}/release-payloads/${GITHUB_REPOSITORY//\\//-}"', "local pin root is scoped to the configured deployment and repository"),
    ('--artifact-name "$MIGRATION_ARTIFACT_NAME"', "legacy artifact fallback uses the configured name"),
    ('RELEASE_PAYLOAD_TRANSPORT="ghcr-container"', "GHCR transport is frozen for new receipts"),
    ('RELEASE_PAYLOAD_TRANSPORT="actions-artifact"', "legacy transport is explicit for older runs"),
]:
    if needle not in selection_download:
        fail(f".github/workflows/cd-localcluster.yml: missing locked artifact selection behavior: {why}")
if "actions/download-artifact@" in cd_localcluster:
    fail(".github/workflows/cd-localcluster.yml: release artifact selection and download must share the host lock")
cd_cloud = read(".github/workflows/cd-cloud.yml")
cloud_selection = workflow_step_text(cd_cloud, "Select successful CI receipt for this commit")
for needle, why in [
    ("find-successful-ci-run.py", "Cloud receipt selector is invoked"),
    ('--target-sha "$GITHUB_SHA"', "Cloud selector binds the dispatched commit"),
    ("--read-final-payload-receipt", "Cloud release requires a run-bound final receipt"),
    ('--payload-app-image-prefix "$RELEASE_PAYLOAD_PREFIX"', "Cloud receipt selection uses the configured package prefix"),
]:
    if needle not in cloud_selection:
        fail(f".github/workflows/cd-cloud.yml: missing immutable migration payload behavior: {why}")
cloud_payload = workflow_step_text(cd_cloud, "Retrieve migration bundle from immutable payload")
for needle, why in [
    ("with-deploy-lock.sh bash -euo pipefail", "Cloud payload retrieval shares the registry deployment lock"),
    ("registry-retention.py --assert-clear", "Cloud retrieval requires no unresolved exact deletion reservation"),
    ("pull_release_payload.py", "Cloud migration payload is pulled and validated by digest"),
    ('--payload-image-prefix "$RELEASE_PAYLOAD_PREFIX"', "Cloud payload pull uses the configured package prefix"),
    ('gh run download "$CI_RUN_ID"', "Cloud legacy fallback uses the exact CI run"),
]:
    if needle not in cloud_payload:
        fail(f".github/workflows/cd-cloud.yml: missing immutable migration payload behavior: {why}")
if "actions/download-artifact@" in cd_cloud:
    fail(".github/workflows/cd-cloud.yml: legacy artifact fallback must use the exact CI run")
artifact_pruner = read("Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py")
for needle, why in [
    ("ACTIVE_STATUSES", "live deployment and producer protection"),
    ('"success", max_runs=100', "bounded successful deployment recovery history"),
    ("successful_shas", "two distinct successful deployment targets"),
    ("the 100 most recent successful deployments", "fail-closed recovery history bound"),
]:
    if needle not in artifact_pruner:
        fail(f"Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py: missing {why}")
maintenance_runner = read("Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh")
for needle, why in [
    ('exec bash "$COMMON_SCRIPT_DIR/with-deploy-lock.sh"', "maintenance runs under the deployment lock"),
    ("prune-actions-runner-residue.sh", "runner residue stage"),
    ("prune-ci-residue.py", "finished-CI residue stage"),
    ("prune-docker-residue.sh", "node-main Docker stage"),
    ("prune-cluster-docker-residue.sh", "cluster Docker stage"),
    ("check-node-main-capacity.sh", "final capacity check"),
]:
    if needle not in maintenance_runner:
        fail(f"Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh: missing {why}")
for path in (
    "Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh",
    "Deployment/Common/Scripts/prune-actions-runner-residue.sh",
    "Deployment/LocalCluster/Scripts/prune-cluster-docker-residue.sh",
    "Deployment/LocalCluster/Scripts/prune-ci-residue.py",
):
    text = read(path)
    if "docker volume prune" in text or "system prune" in text or "volume rm" in text:
        fail(f"{path}: maintenance must never prune Docker volumes or the whole system")
require_contains("Deployment/Common/ansible/roles/mint_base/tasks/main.yml", "mint_base_reboot_after_upgrade | default(true) | bool", "cluster-compatible optional controller reboot")
require_contains("Deployment/Common/ansible/roles/mint_base/tasks/main.yml", "mint_base_install_deploy_key | default(true) | bool", "cluster-compatible optional deploy key")
require_contains("Deployment/Common/ansible/roles/caddy_install/tasks/main.yml", "../../../Common/caddy/Caddyfile", "shared Caddy root configuration")
require_contains("Deployment/LocalCluster/ansible/roles/caddy/meta/main.yml", "- caddy_install", "shared Caddy installation dependency")
require_contains("Deployment/Common/Scripts/prune-actions-runner-residue.sh", "--app-name", "explicit app runner selection")
require_contains(".github/workflows/ci.yml", "bash Deployment/Common/Scripts/Tests/test-ensure-actions-runner-prereqs.sh", "check-only prerequisite fixtures")
if "read-deploy-setting" in read("Deployment/Common/Scripts/prune-actions-runner-residue.sh"):
    fail("Common runner cleanup must not read target settings")
for name in ("docker", "ssh_hardening", "cloudflared", "mint_base", "app_marker"):
    if exists(f"Deployment/LocalCluster/ansible/roles/{name}"):
        fail(f"shared role {name} must not remain at its old target path")
ci_residue = read("Deployment/LocalCluster/Scripts/prune-ci-residue.py")
for needle in ('"Name": ".Name"', "self.network_pattern.fullmatch", "read-deploy-setting.py"):
    if needle not in ci_residue:
        fail("Deployment/LocalCluster/Scripts/prune-ci-residue.py: bind network deletion to the configured app name")
if ".home" in read("Deployment/LocalCluster/Scripts/prune-cluster-docker-residue.sh"):
    fail("Deployment/LocalCluster/Scripts/prune-cluster-docker-residue.sh: do not hard-code a DNS suffix")
if "TESTCONTAINERS_RYUK_DISABLED" in ci:
    fail(".github/workflows/ci.yml: keep Ryuk enabled as the Testcontainers cleanup backstop")
if "actions/setup-python" in ci:
    fail(".github/workflows/ci.yml: use a per-run venv under RUNNER_TEMP, not actions/setup-python")

require_file("Deployment/Common/Scripts/Tests/test_target_gate.py")

# Job structure: PRs validate without publishing; main publishes from a
# separate job that carries the required `build-test-push` check name.
ci_jobs_text = ci.split("jobs:\n", 1)[1] if "jobs:\n" in ci else ""
ci_job_matches = list(re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\n", ci_jobs_text))
ci_jobs = {
    match.group(1): ci_jobs_text[
        match.end():ci_job_matches[index + 1].start() if index + 1 < len(ci_job_matches) else len(ci_jobs_text)
    ]
    for index, match in enumerate(ci_job_matches)
}
allowed_ci_jobs = {"validate", "publish-main", "notify-dependabot-automerge"}
for required_job in ("validate", "publish-main"):
    if required_job not in ci_jobs:
        fail(f".github/workflows/ci.yml: missing required job {required_job}")
if not set(ci_jobs) <= allowed_ci_jobs:
    fail(f".github/workflows/ci.yml: unexpected CI jobs {sorted(set(ci_jobs) - allowed_ci_jobs)}")
for job_id, job_body in ci_jobs.items():
    job_if = re.search(r"(?m)^    if:.*$", job_body)
    job_entry = re.search(r"(?m)^    (?:runs-on|uses):", job_body)
    guarded = job_if is not None and (
        "github.event.pull_request.head.repo.full_name == github.repository" in job_if.group(0)
        or "github.event_name != 'pull_request' && github.ref == 'refs/heads/main'" in job_if.group(0)
    )
    if not guarded or job_entry is None or job_if.start() > job_entry.start():
        fail(f".github/workflows/ci.yml: {job_id} must guard fork PRs before runner allocation")


def workflow_step(job_id: str, step_name: str) -> str:
    match = re.search(
        rf"(?ms)^      - name: {re.escape(step_name)}\n.*?(?=^      - name: |^      # |\Z)",
        ci_jobs.get(job_id, ""),
    )
    if match is None:
        fail(f".github/workflows/ci.yml: missing {step_name} in {job_id}")
        return ""
    return match.group(0)


def workflow_job_permissions(job_id: str) -> str:
    match = re.search(r"(?m)^    permissions:\n(?P<body>(?:^      .*\n)+)", ci_jobs.get(job_id, ""))
    if match is None:
        fail(f".github/workflows/ci.yml: {job_id} needs explicit permissions")
        return ""
    return match.group("body")


if "validate" in ci_jobs and "publish-main" in ci_jobs:
    validate_job = ci_jobs["validate"]
    publisher_job = ci_jobs["publish-main"]
    validate_permissions = workflow_job_permissions("validate")
    publish_permissions = workflow_job_permissions("publish-main")
    if "contents: read" not in validate_permissions or "packages: write" in validate_permissions:
        fail(".github/workflows/ci.yml: validate must have contents: read and no package-write permission")
    if "contents: read" not in publish_permissions or "packages: write" not in publish_permissions:
        fail(".github/workflows/ci.yml: publish-main must own contents: read and packages: write")
    if any("packages: write" in workflow_job_permissions(job_id) for job_id in ci_jobs if job_id != "publish-main"):
        fail(".github/workflows/ci.yml: packages: write must stay scoped to publish-main")
    publisher_gate = workflow_step("publish-main", "Validate required CI results")
    if (
        "name: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && 'validate' || 'build-test-push' }}" not in validate_job
        or "name: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && 'build-test-push' || 'publish-main' }}" not in publisher_job
        or "needs: validate" not in publisher_job
        or "!cancelled()" not in publisher_job
        or "needs.validate.result == 'success'" not in publisher_job
        or publisher_job.find("Validate required CI results") > publisher_job.find("- name: Checkout")
        or "VALIDATE_RESULT: ${{ needs.validate.result }}" not in publisher_gate
        or "Main release requires validate=success" not in publisher_gate
        or "Unexpected CI event/ref" not in publisher_gate
    ):
        fail(".github/workflows/ci.yml: publish-main must keep the build-test-push name on main and fail closed before checkout")
    if "docker/login-action@" in validate_job or "docker push" in validate_job:
        fail(".github/workflows/ci.yml: validate must not log into GHCR or push images")
    if "dotnet ef migrations bundle" not in publisher_job:
        fail(".github/workflows/ci.yml: publish-main must rebuild the bundle from its exact checked-out commit")
    if "actions/upload-artifact@" in ci or "actions/download-artifact@" in ci:
        fail(".github/workflows/ci.yml: routine reports and release payloads must not use Actions artifact storage")
    staging_build = workflow_step("publish-main", "Build migration bundle for this exact publisher run")
    staging_create = workflow_step("publish-main", "Create migration staging provenance")
    staging_validation = workflow_step("publish-main", "Validate migration staging artifact")
    if (
        "dotnet ef migrations bundle" not in staging_build
        or "migration_staging_artifact.py create" not in staging_create
        or "migration_staging_artifact.py validate" not in staging_validation
        or publisher_job.find("Build migration bundle for this exact publisher run") > publisher_job.find("Create migration staging provenance")
        or publisher_job.find("Create migration staging provenance") > publisher_job.find("Validate migration staging artifact")
        or publisher_job.find("Validate migration staging artifact") > publisher_job.find("Build Docker image")
        or publisher_job.find("Validate migration staging artifact") > publisher_job.find("Login to GHCR")
    ):
        fail(".github/workflows/ci.yml: publisher must rebuild, bind, and validate its exact migration bundle before image or registry work")
    if publisher_job.find("ci-docker-smoke.sh") < 0 or publisher_job.find("ci-docker-smoke.sh") > publisher_job.find("Push Docker image"):
        fail(".github/workflows/ci.yml: publish-main must smoke-test the image before pushing it")

    # Every terminal job retains browser diagnostics with its bounded local reports.
    _report_step = workflow_step('validate', 'Store CI reports on this runner')
    if 'cp -a -- BlazorAutoApp.Test/TestResults/Playwright "$report_source/playwright"' not in _report_step or '--source "$report_source"' not in _report_step:
        fail(".github/workflows/ci.yml: terminal report storage must include browser diagnostics")
    _report_step = workflow_step('publish-main', 'Store CI reports on this runner')
    if 'cp -a -- BlazorAutoApp.Test/TestResults/Playwright "$report_source/playwright"' not in _report_step or '--source "$report_source"' not in _report_step:
        fail(".github/workflows/ci.yml: terminal report storage must include browser diagnostics")
    _smoke_reports = read("Deployment/LocalCluster/Scripts/ci-docker-smoke.sh")
    if _smoke_reports.count("/${GITHUB_JOB:-validate}/docker-smoke/") != 3:
        fail("Docker browser smoke must retain TRX under its terminal job report source")
    if any("ci_report_store.py save" not in workflow_step(job_id, "Store CI reports on this runner")
           for job_id in ("validate", "publish-main")):
        fail(".github/workflows/ci.yml: both terminal jobs must store bounded reports locally")
    manifest_step = workflow_step("publish-main", "Resolve pushed image digest and write release manifest")
    if "python3 Scripts/CI/write_release_manifest.py --directory artifacts/migrations" not in manifest_step:
        fail(".github/workflows/ci.yml: selected release must invoke the shared verified manifest writer")
    manifest_writer = read("Scripts/CI/write_release_manifest.py")
    for needle in (
        '"schema_version": 2',
        '"frontend_profile": profile',
        '"acceptance_profile": env["FRONTEND_ACCEPTANCE_PROFILE"]',
        '"image_digest": digest',
        '"ordered_migration_ids"',
        '"bundle_sha256"',
        '"org.opencontainers.image.revision"',
        '"com.blazorautoapp.frontend-profile"',
        '"com.blazorautoapp.acceptance-profile"',
    ):
        if needle not in manifest_writer:
            fail(f"Scripts/CI/write_release_manifest.py: release manifest writer is missing {needle}")
    for needle in ("validate_staging_artifact(", "acceptance_profile_for_frontend(profile)", 'output.open("x"'):
        if needle not in manifest_writer:
            fail(f"Scripts/CI/write_release_manifest.py: missing release validation {needle}")
    release_plan = read("Scripts/CI/frontend_release_plan.py")
    additional_publisher = read("Scripts/CI/publish_additional_frontend.sh")
    settings_step = workflow_step("publish-main", "Load release settings")
    if "ADDITIONAL_FRONTEND_PROFILES: ${{ vars.ADDITIONAL_FRONTEND_PROFILES }}" not in settings_step or "python3 Scripts/CI/frontend_release_plan.py" not in settings_step:
        fail(".github/workflows/ci.yml: optional publication must use the validated release plan")
    for needle in ('if not additional.strip():', 'seen = {selected}', 'acceptance_profile_for_frontend(profile)',
                   "{settings['app_image']}-{profile.lower()}", 'settings.get("release_payload_prefix", "")'):
        if needle not in release_plan:
            fail(f"Scripts/CI/frontend_release_plan.py: missing default isolation or validation {needle}")
    additional_step = workflow_step("publish-main", "Publish additional frontend")
    if ("if: ${{ steps.release_settings.outputs.additional_profile != '' }}" not in additional_step
            or "bash Scripts/CI/publish_additional_frontend.sh" not in additional_step
            or "APP_IMAGE: ${{ steps.release_settings.outputs.additional_image }}" not in additional_step):
        fail(".github/workflows/ci.yml: additional publication must be opt-in with its own image")
    for needle in ('"${primary_image}-${suffix}"', '"$FRONTEND_PROFILE" != "$primary_profile"',
                   "--directory artifacts/additional-migrations", "trap cleanup EXIT", "--cleanup-only",
                   "Scripts/CI/write_release_manifest.py", 'docker image rm "${APP_IMAGE}:${CI_IMAGE_TAG}"'):
        if needle not in additional_publisher:
            fail(f"Scripts/CI/publish_additional_frontend.sh: missing isolated publication check {needle}")
    if (additional_publisher.find("migration_staging_artifact.py validate") > additional_publisher.find("docker build")
            or "bash Deployment/LocalCluster/Scripts/ci-docker-smoke.sh\ndocker tag" not in additional_publisher):
        fail("Scripts/CI/publish_additional_frontend.sh: staging validation and image smoke must precede push")
    additional_cleanup = workflow_step("publish-main", "Remove additional frontend resources after interruption")
    if "always()" not in additional_cleanup or "--cleanup-only" not in additional_cleanup or "outputs.additional_image" not in additional_cleanup:
        fail(".github/workflows/ci.yml: interrupted additional releases require scoped cleanup")
    additional_receipt = workflow_step("publish-main", "Emit immutable release payload receipt")
    for needle in ("ADDITIONAL_PAYLOAD_IMAGE", '--payload-image "${ADDITIONAL_PAYLOAD_IMAGE}"',
                   '--payload-image-prefix "${RELEASE_PAYLOAD_PREFIX}"',
                   "artifacts/additional-migrations/release-manifest.json"):
        if needle not in additional_receipt:
            fail(f".github/workflows/ci.yml: missing additional GHCR payload receipt check {needle}")
    if "Upload additional migration bundle" in publisher_job or "Upload migration bundle" in publisher_job:
        fail(".github/workflows/ci.yml: final migration payloads must not be uploaded as Actions artifacts")

release_validator = read("Deployment/Common/Scripts/validate_release_manifest.py")
shared_release_validator = read("Deployment/Common/Scripts/Component/lib/release_manifest.py")
for needle, why in [
    ("validate_manifest_payload", "adapter uses the shared release identity validator"),
    ("expected_frontend_profile", "manifest bound to target source frontend profile"),
    ("expected_acceptance_profile", "manifest bound to target acceptance profile"),
    ("image_labels", "registry image labels required by manifest validation"),
    ("FRONTEND_PROFILE_LABEL", "baked frontend profile validation"),
    ("ACCEPTANCE_PROFILE_LABEL", "baked acceptance profile validation"),
    ("REVISION_LABEL", "baked source revision validation"),
]:
    if needle not in release_validator:
        fail(f"Deployment/Common/Scripts/validate_release_manifest.py: missing {why}")
for needle, why in [
    ("schema_version not in allowed_schema_versions", "only supported release manifest schemas"),
    ("legacy schema v1 is supported only for verified BlazorAuto releases", "schema-v1 Blazor-only compatibility"),
]:
    if needle not in shared_release_validator:
        fail(f"Deployment/Common/Scripts/Component/lib/release_manifest.py: missing {why}")

deploy_lan = read(".github/workflows/cd-localcluster.yml")
for needle, why in [
    ("name: CD - Deploy LocalCluster", "CD workflow name"),
    ("bash Deployment/Common/Scripts/validate-common-release.sh", "common release validation step"),
    ("actions: read", "permission to inspect CI workflow runs"),
    ("environment:", "GitHub deployment environment"),
    ("LOCALCLUSTER_ENVIRONMENT", "optional side-by-side GitHub environment variable"),
    ("concurrency:", "deployment concurrency guard"),
    ("group: template-registry-payloads", "shared deployment and registry concurrency group"),
    ("LOCALCLUSTER_RUNNER_LABEL", "optional side-by-side runner label variable"),
    ("localcluster", "shared LocalCluster runner label"),
    ("Require main branch", "main branch deployment guard"),
    ("refs/heads/main", "main branch deployment guard"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh app_image", "shared release image setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_bundle_name", "shared migration bundle setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_artifact_name", "shared migration artifact setting"),
    ("bash Deployment/LocalCluster/Scripts/read-deploy-setting.sh public_hostname", "public hostname setting"),
    ('TARGET_SHA="${INPUT_TARGET_SHA:-$GITHUB_SHA}"', "target SHA defaults to the dispatched main commit"),
    ('git merge-base --is-ancestor "$TARGET_SHA" "$GITHUB_SHA"', "only commits on main can deploy"),
    ("echo \"APP_VERSION=${TARGET_SHA}\"", "target commit image tag"),
    ("find-successful-ci-run.py", "successful CI selector for the target commit"),
    ("--target-sha \"$TARGET_SHA\"", "successful CI gate binds the requested target commit"),
    ("--read-final-payload-receipt", "new payload selection requires the final CI receipt"),
    ("CI_RUN_ID=", "CI run id export"),
    ("CI_RUN_ATTEMPT=", "CI run attempt export"),
    ("validate_release_manifest.py", "release manifest validation"),
    ("git show \"${TARGET_SHA}:frontend-profile.txt\"", "frontend profile resolved from selected target commit"),
    ("--legacy-blazor-default", "historical v1 target without a profile file resolves to Blazor"),
    ("TARGET_PROFILE_FILE_PRESENT=${profile_file_present}", "selected profile file presence is recorded"),
    ('if [[ "$RELEASE_MANIFEST_SCHEMA_VERSION" == 2 && "$TARGET_PROFILE_FILE_PRESENT" != true ]]', "schema-v2 target requires its tracked profile file"),
    ('--expected-frontend-profile "$FRONTEND_PROFILE"', "manifest bound to selected frontend profile"),
    ('--expected-acceptance-profile "$ACCEPTANCE_PROFILE"', "manifest bound to selected acceptance profile"),
    ('--image-labels-json "$IMAGE_LABELS_PATH"', "manifest bound to pulled image labels"),
    ('--expected-ci-run-attempt "$CI_RUN_ATTEMPT"', "release manifest bound to the CI attempt"),
    ("release_image_digest=${RELEASE_IMAGE_DIGEST}", "digest-pinned deployment"),
    ('-e @"${GHCR_EXTRA_VARS_FILE}"', "workflow-token registry credentials"),
    ("GHCR_TOKEN: ${{ inputs.local_payload_pin_key == '' && secrets.GITHUB_TOKEN || '' }}", "workflow token is present only when restoring is not local"),
    ('rm -f "${GHCR_EXTRA_VARS_FILE}"', "registry credential file cleanup"),
    ("verify-release-identity.sh", "running release identity verification"),
    ('"${CI_RUN_ATTEMPT}" "${SOURCE_REPO_URL}"', "post-deploy identity checks source repository labels"),
    ("timeout-minutes: 60", "bounded deploy job"),
    ("import_legacy_release_payload.py", "exact CI attempt artifact is digest-verified and pinned"),
    ('--artifact-name "$MIGRATION_ARTIFACT_NAME"', "shared migration artifact download name"),
    ("chmod 0750 \"artifacts/migrations/${MIGRATION_BUNDLE_NAME}\"", "restore migration bundle execute bit"),
    ("bash Deployment/LocalCluster/Scripts/preflight.sh deploy", "deploy preflight"),
    ("with-deploy-lock.sh", "cross-repo deployment lock"),
    ("app_version=${APP_VERSION}", "selected-ref image deployment"),
    ("source_repo_url=${SOURCE_REPO_URL}", "source repository marker metadata"),
    ("${{ github.workspace }}/artifacts/migrations/${MIGRATION_BUNDLE_NAME}", "absolute migration bundle path"),
    ("bash Deployment/LocalCluster/Scripts/acceptance-check.sh", "full acceptance verification"),
    ("mktemp \"${RUNNER_TEMP:-/tmp}/${APP_NAME}_ansible_vault_password.XXXXXX\"", "private vault password temp file"),
    ("rm -f \"${ANSIBLE_VAULT_PASSWORD_FILE}\"", "vault password file cleanup"),
]:
    if needle not in deploy_lan:
        fail(f".github/workflows/cd-localcluster.yml: missing {why}")
download_step = workflow_step_text(deploy_lan, "Select and retrieve the release payload under the shared lock")
if not download_step or "if:" in download_step:
    fail(".github/workflows/cd-localcluster.yml: select and retrieve the release payload under the lock for every deploy")
for needle, why in [
    ("local_payload_pin_key:", "manual dispatch accepts an exact local pin key"),
    ("if: inputs.local_payload_pin_key == ''", "local-pin recovery skips GHCR login"),
    ("--restore \"$pin_dir\"", "local-pin recovery restores the named immutable pin"),
    ('RELEASE_PAYLOAD_TRANSPORT="local-pin"', "local restore is identified to Ansible"),
    ('release_payload_transport=${RELEASE_PAYLOAD_TRANSPORT}', "Ansible receives the frozen payload transport"),
    ("without Actions or GHCR payload access", "offline restore is summarized as an offline path"),
]:
    if needle not in deploy_lan:
        fail(f".github/workflows/cd-localcluster.yml: missing {why}")
if "<<'LOCKED'" not in download_step:
    fail(".github/workflows/cd-localcluster.yml: release selection must use a quoted lock-owned script heredoc")
if "vault_ghcr_token" in read("Deployment/LocalCluster/inventory/prod/vault.example.yml").replace("# vault_ghcr_token", ""):
    fail("Deployment/LocalCluster/inventory/prod/vault.example.yml: GHCR credentials must stay optional")
app_tasks = read("Deployment/LocalCluster/ansible/roles/app/tasks/main.yml")
for needle, why in [
    ("Pull application image with command-owned registry credentials", "single command-owned registry login and pull"),
    ('export DOCKER_CONFIG="$docker_config"', "temporary registry credential store"),
    ('pull_policy="always"', "normal deployment pulls the selected image"),
    ('pull_policy="never"', "offline restore never requests a registry pull"),
    ('docker compose --env-file .compose.env up -d --pull "$pull_policy" --remove-orphans', "pull or start the exact selected image with the Compose allowlist"),
    ("no_log: true", "registry credentials kept out of logs"),
]:
    if needle not in app_tasks:
        fail(f"Deployment/LocalCluster/ansible/roles/app/tasks/main.yml: missing {why}")
if "- name: Log in to GHCR" in app_tasks:
    fail("Deployment/LocalCluster/ansible/roles/app/tasks/main.yml: do not leave a persistent GHCR login on app nodes")
if "when: (release_payload_transport | default('ghcr-container')) != 'local-pin'" not in read("Deployment/LocalCluster/ansible/playbooks/site.yml"):
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: local-pin recovery must skip the network image pull before interruption")
for needle, why in [
    ("Publish LocalCluster release identity for local pin recovery", "current LocalCluster release marker"),
    ("release_payload_pin_key", "LocalCluster release marker retains its exact local pin key"),
    ("release-state/previous.json", "previous LocalCluster release remains available for recovery"),
]:
    if needle not in read("Deployment/LocalCluster/ansible/playbooks/site.yml"):
        fail(f"Deployment/LocalCluster/ansible/playbooks/site.yml: missing {why}")
shared_route_rules = [
    (
        "Append the same scanned key only after the fingerprints match",
        DOC_OWNER_PATHS["ssh_trust"],
        "verified SSH host key acceptance",
    ),
    (
        'cat "$host_key_candidate" >> ~/.ssh/known_hosts',
        DOC_OWNER_PATHS["ssh_trust"],
        "SSH host key acceptance command",
    ),
    (
        "successful `publish-main` job on the same run attempt",
        DOC_OWNER_PATHS["release_contract"],
        "exact-attempt publishing provenance",
    ),
]
for entry_path, documents in (
    (CLUSTER_ENTRY, cluster_guide_documents),
    (FORK_ENTRY, fork_guide_documents),
):
    for needle, owner_path, why in shared_route_rules:
        error = missing_literal(documents, entry_path, owner_path, needle, why)
        if error:
            fail(error)

for document_path, document_text in cluster_guide_documents.items():
    if "Tokens (classic)" in document_text or "vault_ghcr_token: <github-token" in document_text:
        fail(
            f"{document_path}: CD no longer needs a stored GHCR token; do not instruct users to create one"
        )
if "image_tag" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: manual image_tag input should not be required")
if "Deploy Ship To LAN" in deploy_lan or "Deploy App To LAN" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: workflow name must be explicitly CD-oriented")
if "dotnet ef migrations bundle" in deploy_lan or "dotnet restore" in deploy_lan or "dotnet tool restore" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: CD must consume CI artifacts instead of rebuilding them")

registry_workflow = read(".github/workflows/registry-retention.yml")
for needle in ("capacity_recovery_ci_run_id:", "capacity_recovery_ci_attempt:",
               "CAPACITY_RECOVERY_CI_RUN_ID: ${{ inputs.capacity_recovery_ci_run_id }}",
               "CAPACITY_RECOVERY_CI_ATTEMPT: ${{ inputs.capacity_recovery_ci_attempt }}",
               "verify-registry-capacity-recovery.py", "verify-operation-source.py"):
    if needle not in registry_workflow:
        fail("Registry retention must bind explicit capacity recovery inputs and preserve normal source verification")
require_file("Deployment/Common/Scripts/verify-registry-capacity-recovery.py")
require_file("Deployment/Common/Scripts/Tests/test_registry_capacity_recovery.py")
require_contains(".github/workflows/ci.yml", "Deployment/Common/Scripts/Tests/test_registry_capacity_recovery.py",
                 "capacity recovery source proof regression coverage")
registry_dispatch = registry_workflow.split("  workflow_dispatch:", 1)[-1].split("  schedule:", 1)[0]
for needle, why in [
    ("\n    inputs:\n      apply_registry:\n", "manual registry-apply input declaration"),
    ("type: boolean", "boolean registry-apply input"),
    ("default: false", "default-off registry-apply input"),
]:
    if needle not in registry_dispatch:
        fail(f".github/workflows/registry-retention.yml: missing {why}")
for path, workflow in [
    (".github/workflows/ci.yml", read(".github/workflows/ci.yml")),
    (".github/workflows/cd-localcluster.yml", deploy_lan),
    (".github/workflows/cd-localsinglenode.yml", read(".github/workflows/cd-localsinglenode.yml")),
    (".github/workflows/registry-retention.yml", registry_workflow),
]:
    if ("group: template-registry-payloads" not in workflow or "cancel-in-progress: false" not in workflow
            or "queue: max" not in workflow):
        fail(f"{path}: publication, deployment, and retention must share a registry group that preserves pending requests")
actionlint_runner = read("Scripts/CI/run-actionlint.sh")
if ("644076a59742c2d1540ebd4686eab3c308f0e562" not in actionlint_runner
        or "bash Scripts/CI/tests/test-actionlint-queue.sh" not in actionlint_runner):
    fail("Scripts/CI/run-actionlint.sh: require the pinned queue-aware parser and its rejection fixtures")
publish_main = read(".github/workflows/ci.yml").split("  publish-main:", 1)[-1]
for needle, why in [
    ("Enforce final GHCR payload capacity before any registry publication", "final registry admission gate"),
    ("--admission-kind final", "final release reserves full payload size before publication"),
    ("--reserved-bytes", "registry admission accounts for incoming payload bytes"),
    ("--package \"${PRIMARY_PAYLOAD_IMAGE}=private\"", "private package visibility is required for final admission"),
    ('retained_bootstraps=(--retain-manifest "${PRIMARY_PAYLOAD_IMAGE}@sha256:25fef0757d76c56cd980dca6cde1e156ab7a2daa902306ab48da4e12a6e7343f")', "reviewed primary bootstrap is retained by exact digest during admission"),
    ('retained_bootstraps+=(--retain-manifest "${ADDITIONAL_PAYLOAD_IMAGE}@sha256:25fef0757d76c56cd980dca6cde1e156ab7a2daa902306ab48da4e12a6e7343f")', "reviewed React bootstrap is retained by exact digest during admission"),
    ('"${retained_bootstraps[@]}"', "admission verifies reviewed bootstrap manifests"),
]:
    if needle not in publish_main:
        fail(f".github/workflows/ci.yml: missing {why}")
if publish_main.find("Enforce final GHCR payload capacity before any registry publication") > publish_main.find("- name: Build Docker image"):
    fail(".github/workflows/ci.yml: final GHCR capacity gate must precede publication builds")
for needle, why in [
    ("registry_coordination:", "LocalCluster deployment waits for the shared registry reservation check"),
    ("needs: registry_coordination", "LocalCluster deploy job depends on registry reservation check"),
    ("registry-retention.py --assert-clear", "unresolved deletion reservations block LocalCluster deployment"),
]:
    if needle not in deploy_lan:
        fail(f".github/workflows/cd-localcluster.yml: missing {why}")
for needle, why in [
    ('name: GHCR registry retention', "dedicated registry maintenance workflow"),
    ("schedule:", "scheduled registry retention"),
    ('cron: "37 3 * * *"', "daily bounded registry retention"),
    ('retained_bootstraps=(--retain-manifest "${{ steps.packages.outputs.primary }}@sha256:25fef0757d76c56cd980dca6cde1e156ab7a2daa902306ab48da4e12a6e7343f")', "reviewed primary bootstrap is retained by exact digest during registry maintenance"),
    ('retained_bootstraps+=(--retain-manifest "${{ steps.packages.outputs.additional_payload_image }}@sha256:25fef0757d76c56cd980dca6cde1e156ab7a2daa902306ab48da4e12a6e7343f")', "reviewed React bootstrap is retained by exact digest during registry maintenance"),
    ('"${retained_bootstraps[@]}"', "registry maintenance verifies reviewed bootstrap manifests"),
    ("REGISTRY_RETENTION_APPLY: ${{ github.event_name == 'schedule' || inputs.apply_registry == true }}", "scheduled or explicitly opted-in manual registry deletion"),
    ('if [[ "$REGISTRY_RETENTION_APPLY" == "true" ]]; then apply+=(--apply); fi', "manual registry preview unless apply_registry is true"),
    ("localcluster_protection", "LocalCluster current/recovery protections"),
    ("localsinglenode_primary", "primary LocalSingleNode current/recovery protections"),
    ("localsinglenode_additional", "optional additional-app current/recovery protections"),
    ("REGISTRY_COORDINATION_SCOPE_COMPLETE", "all consumer scopes required before deletion"),
    ("with-deploy-lock.sh", "registry deletion runs under the shared deployment lock"),
    ("--apply", "registry retention applies only on schedule or opted-in manual dispatch"),
]:
    if needle not in registry_workflow:
        fail(f".github/workflows/registry-retention.yml: missing {why}")
pull_payload_reader = read("Deployment/Common/Scripts/Component/lib/pull_release_payload.py")
if "assert_selection_available" not in pull_payload_reader:
    fail("Deployment/Common/Scripts/Component/lib/pull_release_payload.py: payload selection must honor live deletion reservations")
manual_deploy = read("Deployment/LocalCluster/Scripts/deploy.sh")
for needle, why in [
    ('git -C "$REPO_ROOT" show "${APP_VERSION}:frontend-profile.txt"', "manual deploy profile resolved from selected source commit"),
    ('release_manifest_schema_version=2', "manual deploy uses schema-v2 identity rules"),
    ('release_source_sha=$APP_VERSION', "manual deploy binds image revision to selected commit"),
]:
    if needle not in manual_deploy:
        fail(f"Deployment/LocalCluster/Scripts/deploy.sh: missing {why}")

for label in (
    "org.opencontainers.image.revision",
    "com.blazorautoapp.frontend-profile",
    "com.blazorautoapp.acceptance-profile",
):
    if label not in release_validator:
        fail(f"release validator must require baked image label {label}")

find_ci = read("Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py")
for needle, why in [
    ("GITHUB_REPOSITORY", "repository input"),
    ("GITHUB_SHA", "commit input"),
    ("GITHUB_TOKEN", "GitHub token input"),
    ("actions/workflows", "workflow runs API"),
    ('selected["conclusion"] != "success"', "successful CI conclusion requirement"),
    ('ALLOWED_EVENTS = {"push", "workflow_dispatch"}', "main push and CI-only workflow dispatch provenance"),
    ('branch != "main"', "main branch run requirement"),
]:
    if needle not in find_ci:
        fail(f"Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py: missing {why}")
require_contains(
    "Deployment/LocalCluster/Scripts/find-successful-ci-run.sh",
    "Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py",
    "LocalCluster successful-CI wrapper points to Common",
)


prepare = read("Deployment/LocalCluster/ansible/playbooks/PrepareFreshLinuxMachine.yml")
role_order = ["mint_base", "ssh_hardening", "docker", "firewall"]
positions = [prepare.find(f"- {role}") for role in role_order]
if any(pos < 0 for pos in positions) or positions != sorted(positions):
    fail("PrepareFreshLinuxMachine.yml: roles must run mint_base, ssh_hardening, docker, firewall")

site = read("Deployment/LocalCluster/ansible/playbooks/site.yml")
for needle, why in [
    ("Apply app firewall rules", "deployment firewall phase"),
    ("firewall", "deployment firewall role"),
    ("hosts: node_db", "node_db deployment phase"),
    ("hosts: load_balancer", "load balancer deployment phase"),
    ("hosts: app_servers", "app server deployment phase"),
    ("Stop app containers before migration", "migration downtime step"),
    ("Check for existing app compose file", "first-deploy-safe migration stop guard"),
    ("site_app_compose_file.stat.exists", "skip app stop only when compose file is absent"),
    ("Create pre-migration database backup", "pre-migration backup"),
    ("./backup-db.sh", "verified backup helper use"),
    ("Run migration bundle", "migration execution"),
    ("ansible.builtin.command:", "migration bundle uses argv without shell evaluation"),
    ("Host=localhost;Port={{ postgres_port }}", "migration connection uses explicit validated deployment inputs"),
    ("Write LocalCluster app ownership markers", "app ownership marker phase"),
    ("app_marker", "app ownership marker role"),
]:
    if needle not in site:
        fail(f"Deployment/LocalCluster/ansible/playbooks/site.yml: missing {why}")
if ". ./.env" in site:
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: migration must not source the raw app environment")
stage_pos = site.find("Stage the exact app image before any app interruption")
stop_pos = site.find("- name: Stop app containers before migration")
apps_pos = site.find("- name: Deploy app servers")
caddy_pos = site.find("- name: Deploy Caddy and Cloudflare Tunnel")
if stage_pos < 0 or stop_pos < 0 or stage_pos > stop_pos:
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: stage the exact app image before stopping apps")
if "Require the registry digest on the staged image" not in site:
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: staged image must be checked against the release digest")
identity_assert_pos = site.find("Require staged release identity before app interruption or migration")
if identity_assert_pos < 0 or identity_assert_pos > stop_pos:
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: check baked release identity before stopping apps or migrating")
for label in (
    "org.opencontainers.image.revision",
    "com.blazorautoapp.frontend-profile",
    "com.blazorautoapp.acceptance-profile",
):
    if label not in site:
        fail(f"Deployment/LocalCluster/ansible/playbooks/site.yml: staged image must match {label}")
apps_play = site[apps_pos:site.find("\n- name:", apps_pos + 1)] if apps_pos >= 0 else ""
if "serial: 1" not in apps_play or "any_errors_fatal: true" not in apps_play:
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: deploy app servers one at a time and stop on the first failure")
if caddy_pos < 0 or caddy_pos < apps_pos:
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: deploy Caddy and Cloudflare Tunnel after app readiness")
if re.search(r"name: Stop existing app stack[\s\S]+?failed_when: false", site):
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: Stop existing app stack must not suppress all failures")

for path, checks in {
    "Deployment/Common/ansible/roles/mint_base/tasks/main.yml": [
        ("name: deploy", "deploy user creation"),
        ("python3-debian", "deb822 repository module dependency"),
        ("NOPASSWD:ALL", "passwordless sudo for automation"),
        ("90-localcluster-deploy", "neutral LocalCluster sudoers file"),
        ("authorized_keys", "deploy SSH public key installation"),
        ("deploy_private_key_file", "control-node private key installation"),
        ("inventory_hostname in groups.get('load_balancer', [])", "private key limited to control node"),
        ("known_hosts", "control-node SSH host key setup"),
        ("ssh-keyscan", "deployment node host key scan"),
        ("path: \"{{ deploy_root }}\"", "deployment root creation"),
    ],
    "Deployment/Common/ansible/roles/docker/tasks/main.yml": [
        ("UBUNTU_CODENAME", "Linux Mint Ubuntu base codename detection"),
        ("docker_ubuntu_codename.stdout | length > 0", "Ubuntu codename non-empty assertion"),
        ("This deployment supports only x86_64/amd64 Linux machines.", "amd64-only Docker guard"),
        ("ansible.builtin.deb822_repository", "deb822 Docker apt repository"),
        ("/etc/apt/sources.list.d/docker.list", "legacy Docker apt repository cleanup"),
        ("signed_by: /etc/apt/keyrings/docker.asc", "Docker keyring-scoped apt repository"),
        ("- amd64", "amd64 Docker apt repository"),
        ("docker-compose-plugin", "Docker Compose plugin"),
        ("groups: docker", "deploy docker group membership"),
    ],
    "Deployment/LocalCluster/ansible/roles/firewall/tasks/main.yml": [
        ("ufw allow OpenSSH", "SSH firewall rule"),
        ("{{ app_name }}-docker-user-firewall.service", "Docker published-port firewall service"),
        ("Apply Docker published-port firewall rules", "Docker published-port firewall rule reapplication"),
        ("groups[\"node_db\"]", "node_db firewall targeting"),
        ("to any port {{ postgres_port }}", "PostgreSQL firewall port"),
        ("to any port {{ redis_port }}", "Redis firewall port"),
    ],
    "Deployment/LocalCluster/ansible/roles/app/templates/app.env.j2": [
        ("COMPOSE_PROJECT_NAME={{ app_name }}", "explicit Compose project name"),
        ("APP_NAME={{ app_name }}", "app identity env marker"),
        ("APP_PORT={{ app_port }}", "app port env rendering"),
        ("APP_IMAGE_REF=", "exact release image reference"),
        ("release_image_digest", "digest-pinned image reference"),
        ("POSTGRES_PORT={{ postgres_port }}", "PostgreSQL port env rendering"),
        ("REDIS_PORT={{ redis_port }}", "Redis port env rendering"),
        ("Accounts__Enabled={{ accounts_enabled | default(false) | string | lower }}", "accounts disabled when settings are absent"),
        ("Accounts__AdminSeed__Password={{ vault_accounts_admin_seed_password | default('') }}", "Admin seed password from the protected vault"),
        ("Accounts__Email__Password={{ vault_accounts_email_password | default('') }}", "SMTP password from the protected vault"),
        ("DataProtection__KeyEncryptionCertificatePath=/run/secrets/data-protection.pem", "read-only app Data Protection certificate path"),
        ("DataProtection__KeyEncryptionCertificatePassword={{ vault_data_protection_certificate_password }}", "app Data Protection certificate passphrase from vault"),
        ("DataProtection__LegacyKeyStore={{ data_protection_legacy_key_store | default('None') }}", "legacy Data Protection source selection"),
        ("DataProtection__LegacyRedisKey={{ data_protection_legacy_redis_key | default('') }}", "legacy Redis repository key"),
        ("/run/legacy-data-protection", "legacy Data Protection source mount path"),
    ],
    "Deployment/LocalCluster/ansible/roles/app/templates/compose.env.j2": [
        ("APP_IMAGE_REF=", "Compose image interpolation input"),
        ("POSTGRES_PASSWORD={{ vault_postgres_password }}", "validated database Compose input"),
        ("REDIS_PASSWORD={{ vault_redis_password }}", "validated Redis Compose input"),
        ("DATA_PROTECTION_CERT_HOST_PATH=/etc/{{ app_name }}/data-protection/certificate.pem", "app Data Protection certificate bind source"),
        ("DATA_PROTECTION_CERT_GID={{ data_protection_certificate_gid }}", "restricted certificate reader group"),
        ("DATA_PROTECTION_LEGACY_HOST_PATH=/etc/{{ app_name }}/data-protection/legacy", "legacy Data Protection bind source"),
    ],
    "Deployment/LocalCluster/ansible/roles/postgres/templates/node-db.env.j2": [
        ("COMPOSE_PROJECT_NAME={{ app_name }}", "explicit Compose project name"),
        ("APP_NAME={{ app_name }}", "node-db app identity env marker"),
        ("POSTGRES_PORT={{ postgres_port }}", "PostgreSQL port env rendering"),
        ("REDIS_PORT={{ redis_port }}", "Redis port env rendering"),
    ],
    "Deployment/Common/ansible/roles/app_marker/tasks/main.yml": [
        ("/etc/localcluster/apps", "app marker directory"),
        ("app-marker.env.j2", "app marker template"),
        ("{{ app_name }}.env", "per-app marker file"),
    ],
    "Deployment/Common/ansible/roles/app_marker/templates/app-marker.env.j2": [
        ("APP_NAME={{ app_name }}", "marker app name"),
        ("DEPLOY_ROOT={{ deploy_root }}", "marker deploy root"),
        ("PUBLIC_HOSTNAME={{ public_hostname }}", "marker public hostname"),
        ("RUNNER_LABEL=", "marker runner label"),
        ("SOURCE_REPO_URL=", "marker source repository"),
    ],
    "Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2": [
        ("DOCKER-USER", "Docker firewall chain"),
        ("APP_CHAIN=", "app-specific Docker firewall chain"),
        ("sha1sum", "short deterministic firewall chain id"),
        ("--ctorigdstport {{ app_port }}", "app port restriction"),
        ("--ctorigdstport {{ postgres_port }}", "PostgreSQL port restriction"),
        ("--ctorigdstport {{ redis_port }}", "Redis port restriction"),
    ],
    "Deployment/LocalCluster/ansible/roles/app/tasks/main.yml": [
        ('pull_policy="always"', "normal deployment pulls the selected image"),
        ('pull_policy="never"', "offline restore avoids registry pulls"),
        ('docker compose --env-file .compose.env up -d --pull "$pull_policy" --remove-orphans', "pull or start requested image with the Compose allowlist"),
        ("vault_data_protection_certificate_base64 | b64decode", "install encrypted app Data Protection certificate"),
        ("mode: \"0440\"", "restrict certificate file to root and app group"),
        ("http://127.0.0.1:{{ app_port }}/health/ready", "local readiness wait"),
        ("version('2.30.0', '>=', version_type='loose')", "raw env-file Compose minimum version"),
        ("data_protection_legacy_key_store", "validated legacy Data Protection source selection"),
        ("/data-protection/legacy", "protected legacy Data Protection source directory"),
        ("no_log: true", "account secret validation output redaction"),
    ],
    "Deployment/LocalCluster/ansible/roles/postgres/tasks/main.yml": [
        ("compose/node-db/docker-compose.yml", "node-db compose source"),
        ("node-db.env.j2", "node-db env template"),
        ("backup-db.sh", "backup helper copy"),
        ("restore-db.sh", "restore helper copy"),
        ("docker compose up -d --pull always", "pull and start pinned database images"),
        ("-e REDISCLI_AUTH redis redis-cli ping", "Redis readiness forwards environment authentication"),
        ("REDISCLI_AUTH: \"{{ vault_redis_password }}\"", "Redis readiness receives password through environment"),
    ],
    "Deployment/LocalCluster/ansible/roles/caddy/templates/app.caddy.j2": [
        ("http://{{ public_hostname }}", "hostname-based Caddy listener for side-by-side apps"),
        ("bind 127.0.0.1", "loopback-only Caddy listener"),
        ("health_uri /health/ready", "readiness health check"),
        ("health_interval 5s", "fast Caddy upstream health recovery"),
        ("health_timeout 2s", "bounded Caddy upstream health checks"),
        ("lb_policy cookie {{ app_name }}_lb", "sticky sessions for Blazor Server"),
    ],
}.items():
    text = read(path)
    for needle, why in checks:
        if needle not in text:
            fail(f"{path}: missing {why}")

for path in [
    "Deployment/LocalCluster/compose/app-server/docker-compose.yml",
    "Deployment/Cloud/compose/app-server/docker-compose.yml",
]:
    compose_text = read(path)
    if "format: raw" not in compose_text or "path: ./.env" not in compose_text:
        fail(f"{path}: app service must consume its protected env file in raw mode")
    if re.search(r"^\s+Accounts__(?:AdminSeed__Password|Email__Username|Email__Password):", compose_text, re.MULTILINE):
        fail(f"{path}: account credentials must not be duplicated in Compose interpolation")
    if "target: /run/secrets/data-protection.pem" not in compose_text or "read_only: true" not in compose_text:
        fail(f"{path}: app Data Protection certificate must be mounted read-only")
    if "target: /run/legacy-data-protection" not in compose_text or "read_only: true" not in compose_text:
        fail(f"{path}: legacy Data Protection source must be mounted read-only")
    if "DATA_PROTECTION_CERT_GID" not in compose_text:
        fail(f"{path}: app Data Protection certificate group must be explicit")

for path, needles in {
    "Deployment/Cloud/ansible/roles/app/templates/app.env.j2": [
        ("Accounts__Enabled={{ accounts_enabled | default(false) | string | lower }}", "accounts disabled when settings are absent"),
        ("Accounts__AdminSeed__Password={{ cloud_accounts_admin_seed_password | default('') }}", "Admin seed password from an optional workflow secret"),
        ("Accounts__Email__Password={{ cloud_accounts_email_password | default('') }}", "SMTP password from an optional workflow secret"),
        ("DataProtection__KeyEncryptionCertificatePath=/run/secrets/data-protection.pem", "read-only app Data Protection certificate path"),
        ("DataProtection__KeyEncryptionCertificatePassword={{ cloud_data_protection_certificate_password }}", "app Data Protection certificate passphrase from workflow secret"),
        ("DataProtection__LegacyKeyStore={{ data_protection_legacy_key_store | default('None') }}", "legacy Data Protection source selection"),
        ("DataProtection__LegacyRedisKey={{ data_protection_legacy_redis_key | default('') }}", "legacy Redis repository key"),
        ("/run/legacy-data-protection", "legacy Data Protection source mount path"),
    ],
    "Deployment/Cloud/ansible/roles/app/templates/compose.env.j2": [
        ("APP_IMAGE={{ app_image }}", "Compose image interpolation input"),
        ("POSTGRES_PASSWORD={{ cloud_postgres_password }}", "database Compose input"),
        ("REDIS_PASSWORD={{ cloud_redis_password }}", "Redis Compose input"),
        ("DATA_PROTECTION_CERT_HOST_PATH=/etc/{{ app_name }}/data-protection/certificate.pem", "app Data Protection certificate bind source"),
        ("DATA_PROTECTION_CERT_GID={{ data_protection_certificate_gid }}", "restricted certificate reader group"),
        ("DATA_PROTECTION_LEGACY_HOST_PATH=/etc/{{ app_name }}/data-protection/legacy", "legacy Data Protection bind source"),
    ],
    "Deployment/Cloud/ansible/roles/app/tasks/main.yml": [
        ("version('2.30.0', '>=', version_type='loose')", "raw env-file Compose minimum version"),
        ("data_protection_legacy_key_store", "validated legacy Data Protection source selection"),
        ("/data-protection/legacy", "protected legacy Data Protection source directory"),
        ("cloud_postgres_password is match('^[A-Za-z0-9._@%+/=-]{16,128}$')", "Compose-safe Cloud database password"),
        ("cloud_redis_password is match('^[A-Za-z0-9._@%+/=-]{16,128}$')", "Compose-safe Cloud Redis password"),
        ("cloud_data_protection_certificate_base64 | b64decode", "install encrypted app Data Protection certificate"),
        ("cloud_data_protection_certificate_password is match('^[A-Fa-f0-9]{64}$')", "strong Cloud Data Protection passphrase"),
        ("Render Compose interpolation allowlist", "account-free Compose input file"),
        ("docker compose --env-file .compose.env up -d --pull always", "Compose runs without parsing raw account settings"),
        ("no_log: true", "account secret validation output redaction"),
    ],
    "Deployment/Cloud/ansible/roles/data/tasks/main.yml": [
        ("cloud_postgres_password is match('^[A-Za-z0-9._@%+/=-]{16,128}$')", "Compose-safe Cloud database password"),
        ("cloud_redis_password is match('^[A-Za-z0-9._@%+/=-]{16,128}$')", "Compose-safe Cloud Redis password"),
    ],
    "Deployment/Cloud/Scripts/Component/lib/cloud_settings.py": [
        ("ACCOUNT_SETTING_KEYS", "explicit account settings allowlist"),
        ("validate_account_deploy_settings(values)", "shared account settings validation"),
        ("LEGACY_DATA_PROTECTION_SETTING_KEYS", "explicit legacy Data Protection settings allowlist"),
        ("validate_legacy_data_protection_settings(values)", "legacy Data Protection source validation"),
    ],
    "Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py": [
        ("LEGACY_DATA_PROTECTION_SETTING_KEYS", "explicit legacy Data Protection settings allowlist"),
        ("validate_legacy_data_protection_settings(values)", "legacy Data Protection source validation"),
    ],
    "Deployment/Common/Scripts/Component/lib/data_protection_deploy_settings.py": [
        ("FileSystem", "FileSystem source support"),
        ("Redis", "Redis source support"),
        ("single-line value", "single-line Redis key validation"),
    ],
    "Deployment/Cloud/Scripts/deploy.sh": [
        ("cloud_accounts_admin_seed_password", "optional Admin seed credential forwarding"),
        ("cloud_accounts_email_password", "optional SMTP credential forwarding"),
        ("cloud_data_protection_certificate_base64", "Cloud certificate secret forwarding"),
        ("cloud_data_protection_certificate_password", "Cloud certificate passphrase forwarding"),
    ],
    "Deployment/Cloud/Scripts/configure-github-environment.sh": [
        ("CLOUD_ACCOUNTS_ADMIN_SEED_PASSWORD", "optional Admin seed workflow secret"),
        ("set_secret_if_missing_body", "preserve existing optional workflow secrets"),
        ("CLOUD_DATA_PROTECTION_CERTIFICATE_BASE64", "stable app certificate workflow secret"),
        ("CLOUD_DATA_PROTECTION_CERTIFICATE_PASSWORD", "stable app certificate passphrase workflow secret"),
    ],
    "Deployment/Cloud/Scripts/check-github-environment.sh": [
        ("CLOUD_DATA_PROTECTION_CERTIFICATE_BASE64", "required encrypted Data Protection certificate secret"),
        ("CLOUD_DATA_PROTECTION_CERTIFICATE_PASSWORD", "required Data Protection certificate passphrase secret"),
    ],
}.items():
    text = read(path)
    for needle, why in needles:
        if needle not in text:
            fail(f"{path}: missing {why}: {needle}")

cloud_deploy_playbook = read("Deployment/Cloud/ansible/playbooks/deploy.yml")
if ". ./.env" in cloud_deploy_playbook:
    fail("Deployment/Cloud/ansible/playbooks/deploy.yml: migration must not source an environment file in a shell")
for needle, why in [
    ("docker compose --env-file .compose.env down", "app stop uses the Compose allowlist"),
    ("ansible.builtin.command:", "migration bundle uses argv without shell evaluation"),
    ("Host=127.0.0.1;Port={{ postgres_port }}", "migration connection uses explicit deployment inputs"),
]:
    if needle not in cloud_deploy_playbook:
        fail(f"Deployment/Cloud/ansible/playbooks/deploy.yml: missing {why}")

require_contains(
    ".github/workflows/cd-cloud.yml",
    "CLOUD_ACCOUNTS_EMAIL_PASSWORD: ${{ secrets.CLOUD_ACCOUNTS_EMAIL_PASSWORD }}",
    "optional Cloud SMTP secret forwarding",
)
if "90-{{ app_name }}-deploy" in read("Deployment/Common/ansible/roles/mint_base/tasks/main.yml"):
    fail("Deployment/Common/ansible/roles/mint_base/tasks/main.yml: sudoers file must be cluster-neutral, not app-named")
if "iptables -F DOCKER-USER" in read("Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2"):
    fail("Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2: must not flush shared DOCKER-USER chain")
require_not_contains(
    "Deployment/LocalCluster/Scripts/acceptance-check.sh",
    'case "$postgres_version"',
    "fragile PostgreSQL version shell pattern",
)
require_not_contains(
    "Deployment/LocalCluster/Scripts/acceptance-check.sh",
    'case "$redis_version"',
    "fragile Redis version shell pattern",
)


preflight = read("Deployment/LocalCluster/Scripts/preflight.sh")
for needle, why in [
    ("REPLACE_WITH", "inventory placeholder detection"),
    ("ansible-inventory", "inventory parse check"),
    ("BOOTSTRAP_INVENTORY", "bootstrap inventory path"),
    ("missing bootstrap inventory", "bootstrap inventory existence check"),
    ("bootstrap-hosts.yml", "bootstrap inventory validation"),
    ("validate-deploy-settings.py", "deployment settings validation"),
    ("vault.yml", "vault existence check"),
    ("check-vault.sh", "deploy vault content check"),
    ("check-port-collisions.sh", "side-by-side port collision check"),
    ("validate-side-by-side.sh", "marker-based side-by-side collision check"),
]:
    if needle not in preflight:
        fail(f"Deployment/LocalCluster/Scripts/preflight.sh: missing {why}")

check_port_collisions = read("Deployment/LocalCluster/Scripts/check-port-collisions.sh")
for needle, why in [
    ("app_port", "app port setting"),
    ("postgres_port", "PostgreSQL port setting"),
    ("redis_port", "Redis port setting"),
    ("APP_NAME", "deploy root identity marker"),
    ("belongs to app", "wrong deploy root owner failure"),
    ("ss -H -ltn", "listening port detection"),
    ("docker compose ps -q", "existing same-app deployment allowance"),
    ("port collision check ok", "clear success line"),
]:
    if needle not in check_port_collisions:
        fail(f"Deployment/LocalCluster/Scripts/check-port-collisions.sh: missing {why}")

for path, checks in {
    "Deployment/LocalCluster/Scripts/summary.sh": [
        ("from deploy_settings import load_settings", "shared settings reader"),
        ("Target nodes", "target node summary"),
        ("BLOCKER", "placeholder blocker labeling"),
        ("runner_label", "runner label summary"),
    ],
    "Deployment/LocalCluster/Scripts/validate-machines.sh": [
        ("generate-inventory.py", "shared inventory parser reuse"),
        ("--check", "read-only machines validation mode"),
    ],
    "Deployment/LocalCluster/Scripts/doctor.sh": [
        ("summary.sh", "summary reuse"),
        ("validate-deploy-settings.py", "settings validation"),
        ("check-vault.sh", "vault validation"),
        ("validate-side-by-side.sh", "side-by-side validation"),
        ("Next likely action", "next action output"),
    ],
    "Deployment/LocalCluster/Scripts/prepare-existing-localcluster-app.sh": [
        ("--existing-key", "existing deploy key argument"),
        ("LOCALCLUSTER_EXISTING_DEPLOY_KEY", "existing deploy key environment fallback"),
        ("PrepareExistingLocalClusterApp.yml", "existing cluster preparation playbook"),
        ("ansible_ssh_private_key_file=$EXISTING_KEY", "old key override during preparation"),
        ("new deploy key installed", "clear success line"),
    ],
    "Deployment/LocalCluster/Scripts/acceptance-check.sh": [
        ("https://${PUBLIC_HOSTNAME}/health/ready", "public health check"),
        ("ANSIBLE_CONFIG", "LocalCluster Ansible config for ad-hoc checks"),
        ("Host: \\$PUBLIC_HOSTNAME", "hostname-aware local Caddy check"),
        ("local Caddy health still failed after 120 seconds", "local Caddy retry diagnostics"),
        ("wait_for_public_health", "public health retry"),
        ("--services --filter status=running", "running compose service checks"),
        ("grep -Fx web", "visible app service check"),
        ("pg_isready", "PostgreSQL health check"),
        ("redis-cli", "Redis health check"),
        ("REDISCLI_AUTH", "Redis auth environment"),
        ("grep -Fx PONG", "strict Redis PONG check"),
        ("PostgreSQL 18", "PostgreSQL 18 version check"),
        ("v=8", "Redis 8 version check"),
        ("grep -Fq '(PostgreSQL) 18.4'", "fixed-string PostgreSQL version check"),
        ("grep -Fq 'v=8.8.0'", "fixed-string Redis version check"),
        ("expected PostgreSQL 18.4, got:", "diagnostic PostgreSQL version mismatch"),
        ("expected Redis 8.8.0, got:", "diagnostic Redis version mismatch"),
        ("sport = :${POSTGRES_PORT}", "PostgreSQL port check"),
        ("sport = :${REDIS_PORT}", "Redis port check"),
        ("backup directory", "backup directory check"),
        ('echo "acceptance check ok"', "canonical command success line"),
    ],
    "Deployment/LocalCluster/Scripts/report-nodes.sh": [
        ("os=", "OS report"),
        ("docker=", "Docker report"),
        ("ufw=", "UFW report"),
        ("listening_ports=", "listening port report"),
    ],
    "Deployment/LocalCluster/Scripts/list-deployed-apps.sh": [
        ("/etc/localcluster/apps/*.env", "app marker discovery"),
        ("RUNNER_LABEL", "runner label output"),
        ("CLOUDFLARE_TUNNEL_NAME", "tunnel output"),
    ],
    "Deployment/LocalCluster/Scripts/validate-side-by-side.sh": [
        ("/etc/localcluster/apps/*.env", "app marker discovery"),
        ("check_conflict app_port", "app port collision check"),
        ("check_conflict postgres_port", "PostgreSQL port collision check"),
        ("check_conflict redis_port", "Redis port collision check"),
        ("check_conflict public_hostname", "public hostname collision check"),
        ("check_conflict runner_label", "runner label collision check"),
        ("side-by-side validation ok", "clear success line"),
    ],
    "Deployment/LocalCluster/Scripts/verify-backup.sh": [
        ("gzip -t", "gzip integrity check"),
        ("PostgreSQL database dump|SET", "plain SQL plausibility check"),
        ("printf -v BACKUP_ARG_Q", "remote backup argument shell quoting"),
        ("backup verification ok", "clear success line"),
    ],
    "Deployment/LocalCluster/Scripts/check-github-runner.sh": [
        ("gh api", "GitHub API runner lookup"),
        ("RUNNER_LABEL", "runner label check"),
        ("no matching runner is online", "runner online check"),
        ("unexpected custom labels", "stale custom label rejection"),
    ],
    "Deployment/LocalCluster/Scripts/check-cloudflare-tunnel.sh": [
        ("CLOUDFLARE_ACCOUNT_ID", "Cloudflare account input"),
        ("method=\"GET\"", "read-only Cloudflare API use"),
        ("http://127.0.0.1:80", "expected tunnel service URL"),
        ("DNS CNAME", "DNS record check"),
    ],
    "Deployment/LocalCluster/Scripts/validate-rendered-templates.sh": [
        ("render_caddy", "Caddy render fixture"),
        ("secondnotes.example.com", "two-app render fixture"),
        ("COMPOSE_PROJECT_NAME=notes", "explicit Compose project render check"),
        ('["docker", "compose"', "optional Compose validation"),
        ("rendered template validation ok", "clear success line"),
    ],
    "Deployment/LocalCluster/Scripts/Component/node-db/backup-db.sh": [
        ("gzip -t", "gzip integrity check"),
        ("TEMP_BACKUP", "temporary backup file before verified move"),
        ("mv \"$TEMP_BACKUP\" \"$BACKUP\"", "publish only verified backup"),
        ("backup path:", "backup path output"),
        ("backup verification ok", "backup verification success line"),
    ],
    "Deployment/LocalCluster/Scripts/Component/node-db/restore-db.sh": [
        ("--confirm", "explicit restore confirmation argument"),
        ("${APP_NAME}/${POSTGRES_DB}", "app/database confirmation token"),
        ("gzip -t", "backup integrity check before restore"),
        ("database restore complete", "restore completion line"),
    ],
}.items():
    text = read(path)
    for needle, why in checks:
        if needle not in text:
            fail(f"{path}: missing {why}")

support_ping = read("Deployment/LocalCluster/Scripts/Component/ping-fresh-machines.sh")
for needle, why in [
    ('SCRIPTS_DIR="$(cd -P "$SCRIPT_DIR/.." && pwd)"', "parent scripts directory resolution"),
    ('REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../../.." && pwd)"', "support script repo-root depth"),
    ('bash "$SCRIPTS_DIR/preflight.sh" bootstrap', "preflight called from parent scripts directory"),
    ('-i "$BOOTSTRAP_INVENTORY"', "absolute bootstrap inventory path"),
    ("Resolved scripts directory", "path debugging output"),
]:
    if needle not in support_ping:
        fail(f"Deployment/LocalCluster/Scripts/Component/ping-fresh-machines.sh: missing {why}")
if 'bash "$SCRIPT_DIR/preflight.sh"' in support_ping:
    fail("Deployment/LocalCluster/Scripts/Component/ping-fresh-machines.sh: must not look for preflight.sh inside Scripts/Component")
if 'REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"' in support_ping:
    fail("Deployment/LocalCluster/Scripts/Component/ping-fresh-machines.sh: Component scripts need four levels to reach repo root")

deploy_lock = read("Deployment/Common/Scripts/Component/with-deploy-lock.sh")
for needle, why in [
    ("mkdir \"$LOCK_DIR\"", "directory-based cross-repo deployment lock"),
    ("LOCALCLUSTER_DEPLOY_LOCK_DIR", "configurable lock directory"),
    ("LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS", "configurable lock timeout"),
    ("release_lock", "token-checked lock release"),
    ("wait_for_owned_command_then_exit", "lock held until the owned command exits"),
    ("trap 'handle_signal 143' TERM", "termination handling that keeps the lock"),
    ("! -name token ! -name owner ! -name created_epoch", "foreign lock metadata protection"),
]:
    if needle not in deploy_lock:
        fail(f"Deployment/Common/Scripts/Component/with-deploy-lock.sh: missing {why}")
# A shared lock must never be reclaimed by age: a dead shell can leave live
# children, and another app on the same node-main may hold it for hours.
for lock_script in (
    "Deployment/Common/Scripts/Component/with-deploy-lock.sh",
    "Deployment/LocalCluster/Scripts/Component/with-node-main-deploy-lock.sh",
):
    for forbidden in ("LOCK_STALE_SECONDS", "cleanup_stale_lock", "StrictHostKeyChecking=accept-new"):
        require_not_contains(lock_script, forbidden, "automatic or unverified deployment lock handling")

node_main_deploy_lock = read("Deployment/LocalCluster/Scripts/Component/with-node-main-deploy-lock.sh")
for needle, why in [
    ("ansible-inventory", "node-main lookup from inventory"),
    ("node-main", "node-main remote lock target"),
    ("ssh", "remote lock transport"),
    ("try_acquire_lock", "remote lock acquisition"),
    ("LOCALCLUSTER_DEPLOY_LOCK_DIR", "shared lock directory"),
    ("! -name token ! -name owner ! -name created_epoch", "foreign lock metadata protection"),
]:
    if needle not in node_main_deploy_lock:
        fail(f"Deployment/LocalCluster/Scripts/Component/with-node-main-deploy-lock.sh: missing {why}")
require_contains(
    "Deployment/LocalCluster/Scripts/deploy.sh",
    "Component/with-node-main-deploy-lock.sh",
    "manual deploy node-main lock wrapper",
)
for needle, why in [
    ("--migrate", "migration bundle CLI option"),
    ("run_migrations=true", "migration Ansible switch"),
    ("migration_bundle_local_path", "migration bundle forwarding"),
]:
    require_contains("Deployment/LocalCluster/Scripts/deploy.sh", needle, why)

for path in [
    "Deployment/LocalCluster/Scripts/Component/ping-fresh-machines.sh",
    "Deployment/LocalCluster/Scripts/prepare-fresh-linux-machines.sh",
]:
    require_contains(path, "ANSIBLE_HOST_KEY_CHECKING=False", "bootstrap host-key bypass for password SSH")

check_vault = read("Deployment/LocalCluster/Scripts/check-vault.sh")
for needle, why in [
    ("ansible-vault view", "vault decrypt validation"),
    ("REPLACE_WITH", "placeholder rejection"),
    ("validate-vault.py", "strict vault value validation"),
]:
    if needle not in check_vault:
        fail(f"Deployment/LocalCluster/Scripts/check-vault.sh: missing {why}")

validate_vault = read("Deployment/LocalCluster/Scripts/Component/lib/validate-vault.py")
for needle, why in [
    ("duplicate key", "duplicate vault key rejection"),
    ("DOTENV_SAFE_PASSWORD", "dotenv-safe DB/Redis password validation"),
    ("vault_cloudflare_tunnel_token", "Cloudflare token key validation"),
    ("vault_ghcr_token", "GHCR token key validation"),
    ("vault_data_protection_certificate_base64", "encrypted app Data Protection certificate validation"),
    ("vault_data_protection_certificate_password", "app Data Protection passphrase validation"),
    ("unknown key", "unknown vault key rejection"),
]:
    if needle not in validate_vault:
        fail(f"Deployment/LocalCluster/Scripts/Component/lib/validate-vault.py: missing {why}")

setup_secrets = read("Deployment/LocalCluster/Scripts/setup-secrets.sh")
for needle, why in [
    ("gh secret set ANSIBLE_VAULT_PASSWORD", "GitHub vault password secret automation"),
    ("could not set the GitHub repository secret automatically", "manual GitHub secret fallback"),
    ("ansible-vault edit", "vault editing"),
    ("check-vault.sh", "vault validation"),
    ("data_protection_vault.py", "preserve-or-generate protected certificate vault update"),
    ("openssl rand -hex 32", "high-entropy encrypted certificate passphrase generation"),
]:
    if needle not in setup_secrets:
        fail(f"Deployment/LocalCluster/Scripts/setup-secrets.sh: missing {why}")
if "--body-file" in setup_secrets:
    fail("Deployment/LocalCluster/Scripts/setup-secrets.sh: gh secret set must read from stdin, not unsupported --body-file")

verify_bootstrap = read("Deployment/LocalCluster/Scripts/verify-bootstrap.sh")
for needle, why in [
    ("status.sh\" bootstrap", "bootstrap status check"),
    ("Component/ping-fresh-machines.sh", "fresh-machine ping check"),
    ("missing required script", "clear missing dependency error"),
    ("Resolved scripts directory", "path debugging output"),
    ("repository checkout is stale or incomplete", "stale checkout guidance"),
    ("bootstrap verification ok", "clear success line"),
]:
    if needle not in verify_bootstrap:
        fail(f"Deployment/LocalCluster/Scripts/verify-bootstrap.sh: missing {why}")

runner_setup = read("Deployment/LocalCluster/Scripts/install-github-runner.sh")
for needle, why in [
    ("actions/runners/registration-token", "runner registration token automation"),
    ("RUNNER_CONFIGURED", "remote runner reuse check before token creation"),
    ("read-tool-version.py", "shared reviewed runner version and checksum"),
    ("sha256sum --check --status", "published archive checksum verification"),
    ("actions-runner-linux-x64", "x64 runner package"),
    ("this deployment supports only x86_64/amd64 node-main machines", "x64 runner guard"),
    ("RUNNER_TOKEN_Q", "runner token kept out of ssh command arguments"),
    ("unset RUNNER_TOKEN", "runner token unset after configuration"),
    ("RUNNER_LABEL", "app-specific runner label setting"),
    ("localcluster,${RUNNER_LABEL}", "shared and app-specific runner label configuration"),
    ("gh api -X PUT", "exact runner custom label repair"),
    ("actions/runners/$RUNNER_ID/labels", "runner label repair API call"),
    ("check-github-runner.sh", "post-install runner verification"),
    ("agentName", "configured runner name verification"),
    ("has unreadable or incomplete identity; inspect it manually", "fail-closed handling of an unreadable runner identity"),
    ("/opt/actions-runner-${APP_NAME}", "app-specific runner directory"),
    ("sudo ./svc.sh install deploy", "runner service install as deploy"),
]:
    if needle not in runner_setup:
        fail(f"Deployment/LocalCluster/Scripts/install-github-runner.sh: missing {why}")
if "RUNNER_NEEDS_RECONFIGURE" in runner_setup or "-exec rm -rf" in runner_setup:
    fail("Deployment/LocalCluster/Scripts/install-github-runner.sh: never delete a runner directory automatically")
runner_configured_pos = runner_setup.find("RUNNER_CONFIGURED=")
runner_token_pos = runner_setup.find('RUNNER_TOKEN="$(gh api')
if runner_configured_pos < 0 or runner_token_pos < 0 or runner_token_pos < runner_configured_pos:
    fail("Deployment/LocalCluster/Scripts/install-github-runner.sh: check remote runner state before requesting a runner token")
if "RUNNER_TOKEN='$RUNNER_TOKEN'" in runner_setup or 'RUNNER_TOKEN="$RUNNER_TOKEN"' in runner_setup:
    fail("Deployment/LocalCluster/Scripts/install-github-runner.sh: runner token must not be passed in the ssh command arguments")
for forbidden in ["RUNNER_ARCH=", "aarch64", "arm64", "armv7l", "armv6l"]:
    if forbidden in runner_setup:
        fail(f"Deployment/LocalCluster/Scripts/install-github-runner.sh: contains forbidden multi-architecture runner logic: {forbidden}")

setup_cloudflare = read("Deployment/LocalCluster/Scripts/setup-cloudflare-tunnel.sh")
for needle, why in [
    ("CLOUDFLARE_ACCOUNT_ID", "Cloudflare account id input"),
    ("CLOUDFLARE_ZONE_ID", "Cloudflare zone id input"),
    ("CLOUDFLARE_API_TOKEN", "Cloudflare API token input"),
    ("from deploy_settings import load_settings", "shared deployment settings reader"),
    ("cloudflare_tunnel_name", "tunnel name read from deployment settings"),
    ("public_hostname", "public hostname read from deployment settings"),
    ("POST", "Cloudflare tunnel creation"),
    ("cfd_tunnel", "Cloudflare tunnel API endpoint"),
    ("configurations", "Cloudflare tunnel configuration endpoint"),
    ("get_tunnel_config", "existing Cloudflare tunnel config preservation"),
    ("kept_ingress", "side-by-side Cloudflare hostname preservation"),
    ("dns_records", "Cloudflare DNS record endpoint"),
    ("CLOUDFLARE_ALLOW_DNS_REPLACE", "explicit DNS replacement guard"),
    ("vault_cloudflare_tunnel_token", "vault token output"),
]:
    if needle not in setup_cloudflare:
        fail(f"Deployment/LocalCluster/Scripts/setup-cloudflare-tunnel.sh: missing {why}")
if "def read_simple_yaml_value" in setup_cloudflare:
    fail("Deployment/LocalCluster/Scripts/setup-cloudflare-tunnel.sh: use deploy_settings.py instead of a local all.yml parser")
for normal_path in [
    "Deployment/LocalCluster/Scripts/preflight.sh",
    "Deployment/LocalCluster/Scripts/status.sh",
    "Deployment/LocalCluster/Scripts/setup-secrets.sh",
    ".github/workflows/cd-localcluster.yml",
]:
    text = read(normal_path)
    for forbidden in ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_ZONE_ID", "CLOUDFLARE_API_TOKEN"]:
        if forbidden in text:
            fail(f"{normal_path}: Cloudflare API variables must stay optional, not part of the normal deploy path")

workflow_paths = sorted(
    str(path.relative_to(ROOT)).replace("\\", "/")
    for path in (ROOT / ".github" / "workflows").glob("*.yml")
)
if not workflow_paths:
    fail(".github/workflows: no workflow files found")

# Code scanning is the one workflow that runs on a GitHub-hosted runner. It has no secrets, no node access and no
# deployment step, and free CodeQL exists only for public repositories, so it is exempt from the self-hosted rules
# above and held to its own exact rule below.
CODEQL_WORKFLOW = ".github/workflows/codeql.yml"

for workflow in workflow_paths:
    if workflow == CODEQL_WORKFLOW:
        continue
    has_runs_on = False
    for line_number, line in enumerate(read(workflow).splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("runs-on:"):
            continue
        has_runs_on = True
        if "self-hosted" not in stripped:
            fail(f"{workflow}:{line_number}: runs-on must target the node-main self-hosted runner: {stripped}")
        for hosted_runner in ["ubuntu-", "ubuntu-latest", "windows-", "macos-"]:
            if hosted_runner in stripped:
                fail(f"{workflow}:{line_number}: contains forbidden GitHub-hosted runner label: {stripped}")
    if has_runs_on:
        single_node_workflow = "localsinglenode" in Path(workflow).name
        fallback = "localsinglenode-books" if single_node_workflow else "localcluster-books"
        require_contains(workflow, fallback, "app-specific self-hosted runner fallback")
        if workflow in (".github/workflows/ci.yml", ".github/workflows/auto-merge-dependabot.yml"):
            require_contains(workflow, "vars.CI_RUNNER_LABEL || vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books'", "neutral CI label with existing fallback")
            jobs = re.split(r"(?m)^  [a-zA-Z0-9_-]+:\n", read(workflow).split("jobs:\n", 1)[1])[1:]
            for job in jobs:
                if "runs-on:" not in job:
                    continue
                runner_line = re.search(r"(?m)^    runs-on:.*$", job)
                if runner_line is None or "vars.CI_RUNNER_LABEL || vars.LOCALCLUSTER_RUNNER_LABEL || 'localcluster-books'" not in runner_line.group(0):
                    fail(f"{workflow}: every CI job must use the neutral CI label and preserve its fallbacks")
                profile = re.search(r"(?ms)^      - name: Verify CI runner\n.*?(?=^      - name: |\Z)", job)
                if profile is None or any(needle not in profile.group(0) for needle in (
                    "CI_RUNNER_HOST: ${{ vars.CI_RUNNER_HOST }}",
                    "${CI_RUNNER_HOST:?Set the CI_RUNNER_HOST repository variable",
                    'test "$(hostname)" = "$CI_RUNNER_HOST"',
                )):
                    fail(f"{workflow}: every CI job must verify the configured CI host")
        elif single_node_workflow:
            require_contains(workflow, "Verify the intended native node", "explicit native deployment host verification")
            if workflow == ".github/workflows/localsinglenode-readiness.yml":
                require_contains(workflow, "native-readiness.py --verify-only", "protected candidate host verification before Docker inspection")
                require_contains(workflow, "secrets.LOCALSINGLENODE_READINESS_CANDIDATE", "masked native host identity input")
                require_contains("Deployment/LocalSingleNode/Scripts/native-readiness.py", "host != socket.gethostname()", "exact protected single-node host identity")
                require_contains("Deployment/LocalSingleNode/Scripts/native-readiness.py", "read_yaml(ETC / 'localsinglenode/machine.yml', node=True)['name'] != host", "protected host agrees with recorded native facts")
            else:
                require_contains(workflow, 'test "$(hostname)" = "$LOCALSINGLENODE_HOST"', "mandatory configured single-node host")
        else:
            require_contains(workflow, "Verify node-main runner", "explicit node-main runner verification")
    if Path(workflow).name.startswith("cd-") or Path(workflow).name.endswith("-maintenance.yml"):
        target = "cloud" if Path(workflow).name == "cd-cloud.yml" else ("localsinglenode" if "localsinglenode" in Path(workflow).name else "localcluster")
        first_steps = re.findall(r"(?m)^    steps:\n(?P<body>(?:^      .*\n|^        .*\n|^          .*\n|^\n)+)", read(workflow))
        if not first_steps:
            fail(f"{workflow}: deployment workflow must have job steps")
        for steps in first_steps:
            first = re.split(r"(?m)^      - name: ", steps)[1]
            for needle in (
                "Require this deployment target to be enabled\n",
                "DEPLOY_TARGETS: ${{ vars.DEPLOY_TARGETS }}",
                f"TARGET: {target}\n",
                'targets=",${DEPLOY_TARGETS// /},"',
                'if [[ "$targets" != *",${TARGET},"* ]]; then',
                'exit 1',
            ):
                if needle not in first:
                    fail(f"{workflow}: each deployment job must fail closed on an exact enabled-target match before other steps")

release_status_workflow = read(".github/workflows/release-status.yml")
for needle, why in (
    ("workflow_dispatch:", "manual-only read-only status trigger"),
    ("permissions:\n  actions: read\n  contents: read\n", "read-only Actions and contents permissions"),
    ("template-release-status-${{ inputs.target }}-${{ inputs.target == 'localsinglenode' && inputs.app_instance || 'primary' }}", "target and instance-specific serialization"),
    ("cancel-in-progress: false", "non-canceling status serialization"),
    ("Require trusted main", "trusted main-only status source"),
    ('test "$GITHUB_REF" = refs/heads/main', "status code restricted to main"),
    ("Require this deployment target to be enabled", "enabled deployment target gate"),
    ("Verify node-main runner", "explicit LocalCluster runner identity verification"),
    ("read-deploy-setting.py runner_name", "configured LocalCluster runner identity"),
    ("with-deploy-lock.sh", "shared deployment lock for status inspection"),
    ('value.get("mutation") != "none"', "workflow rejects any reported mutation"),
    ('value.get("shared_lock") != "held"', "workflow requires the shared lock"),
    ("GITHUB_STEP_SUMMARY", "bounded human-readable status output"),
    ("secrets.GITHUB_TOKEN", "short-lived read-only Actions status token"),
    ("verify_offline_pins:", "opt-in offline restoration verification for exact local pins"),
    ("VERIFY_OFFLINE_PINS: ${{ inputs.verify_offline_pins }}", "offline pin verification input wired to status jobs"),
    ("localsinglenode-books", "LocalSingleNode runner label fallback"),
):
    if needle not in release_status_workflow:
        fail(f".github/workflows/release-status.yml: missing {why}: {needle}")
for forbidden, why in (
    ("schedule:", "scheduled trigger"),
    ("pull_request:", "pull request trigger"),
    ("actions: write", "Actions write permission"),
    ("packages: write", "package write permission"),
    ("docker push", "registry publication"),
    ("gh api -X DELETE", "GitHub resource deletion"),
):
    if forbidden in release_status_workflow:
        fail(f".github/workflows/release-status.yml: must not use {why}: {forbidden}")
for status_script in (
    "Deployment/LocalCluster/Scripts/release-status.py",
    "Deployment/LocalSingleNode/Scripts/release-status.py",
):
    for needle, why in (
        ("pin_release_payload.prune_local_pins(", "the existing local pin inventory"),
        ("apply=False", "dry-run pin inventory with no deletion"),
        ("verify_offline_pin_restore(", "optional offline restoration of verified current and recovery pins"),
        ('"mutation": "none"', "an explicit no-mutation result"),
        ("list_active_deployment_runs(", "active deployment run identities"),
        ("_require_shared_lock()", "the existing deployment lock ownership proof"),
    ):
        if needle not in read(status_script):
            fail(f"{status_script}: missing {why}: {needle}")
for needle, why in (
    ("ACTIVE_STATUSES = (\"queued\", \"in_progress\", \"waiting\", \"requested\", \"pending\")", "all active and waiting Actions states"),
    ("target_sha", "the requested deployment target SHA"),
    ("run_attempt", "the exact workflow run attempt"),
    ('"Authorization": f"Bearer {token}"', "the runner-provided short-lived API token"),
    ("os.environ.pop(name)", "GitHub and registry credentials removed during offline local pin restoration"),
    ("sha256_file(path) != digest", "restored payload bytes checked against their frozen checksums"),
):
    if needle not in read("Deployment/Common/Scripts/Component/lib/release_status.py"):
        fail(f"Deployment/Common/Scripts/Component/lib/release_status.py: missing {why}: {needle}")
if CODEQL_WORKFLOW in workflow_paths:
    codeql = read(CODEQL_WORKFLOW)
    for needle, why in (
        ("    runs-on: ubuntu-latest\n", "the single GitHub-hosted runner of the code-scanning job"),
        ("permissions:\n  contents: read\n", "a read-only default token"),
        ("      security-events: write\n", "the code-scanning upload permission on the job"),
        ("if: ${{ !github.event.repository.private }}", "the public-repository guard"),
        ("github/codeql-action/init@", "the CodeQL init action"),
        ("github/codeql-action/analyze@", "the CodeQL analyze action"),
    ):
        if needle not in codeql:
            fail(f"{CODEQL_WORKFLOW}: missing {why}: {needle.strip()}")
    for forbidden, why in (
        ("secrets.", "secrets"),
        ("vars.", "repository variables"),
        ("pull_request_target", "a privileged fork trigger"),
        ("workflow_dispatch", "a manual trigger"),
    ):
        if forbidden in codeql:
            fail(f"{CODEQL_WORKFLOW}: must not use {why}: {forbidden}")
    if len(re.findall(r"(?m)^\s*runs-on:", codeql)) != 1:
        fail(f"{CODEQL_WORKFLOW}: exactly one job with one GitHub-hosted runner is allowed")
require_contains(
    ".github/workflows/auto-merge-dependabot.yml",
    "Verify GitHub CLI",
    "self-hosted auto-merge gh availability check",
)
# Dependabot auto-merge must merge only the exact commit CI tested, keep major
# bumps and deployment/workflow logic changes for a human, and leave branch
# freshness decisions to GitHub's configured merge rules.
auto_merge = read(".github/workflows/auto-merge-dependabot.yml")
for needle, why in [
    ("startsWith(github.event.workflow_run.head_branch, 'dependabot/')", "Dependabot branch scope"),
    ('"$source_workflow_path" != \'.github/workflows/ci.yml\'', "CI workflow identity check"),
    ('"$head_sha" != "$SOURCE_SHA"', "exact tested head check"),
    ("semver-major", "major update manual review"),
    ("deployment-surface", "deployment surface manual review"),
    ("workflow-change-not-limited-to-action-version-updates", "workflow logic manual review"),
    ("gh pr merge \"$pr\" --disable-auto", "auto-merge disabled when manual review is required"),
    ("CLEAN|BEHIND|BLOCKED|HAS_HOOKS|UNSTABLE)", "behind branch delegated to repository merge rules"),
    ("secrets.GH_TOKEN || secrets.GITHUB_TOKEN", "optional repository write token"),
    ("Auto-merge deferred", "visible deferral reason"),
    ("gh pr merge \"$pr\" --merge --auto", "queued merge after required checks"),
    ('--match-head-commit "$SOURCE_SHA"', "merge restricted to the exact CI-tested head"),
    ('gh workflow run ci.yml --repo "$GH_REPO" --ref main', "main CI after confirmed merge"),
    ('no CD workflow was dispatched', "CI-only post-merge routing"),
]:
    if needle not in auto_merge:
        fail(f".github/workflows/auto-merge-dependabot.yml: missing {why}")
if "/update-branch" in auto_merge:
    fail(".github/workflows/auto-merge-dependabot.yml: do not push base updates to Dependabot workflow branches")
if 'gh workflow run ci.yml --ref "$head_branch"' in auto_merge:
    fail(".github/workflows/auto-merge-dependabot.yml: do not refresh Dependabot branches or rerun their PR CI")
if re.search(r"gh workflow run (?:cd-|.*deploy)", auto_merge):
    fail(".github/workflows/auto-merge-dependabot.yml: Dependabot auto-merge must not dispatch deployment workflows")
if "--delete-branch" in auto_merge:
    fail(".github/workflows/auto-merge-dependabot.yml: do not delete Dependabot branches; Dependabot tracks them")
callback_job = ci_jobs.get("notify-dependabot-automerge")
if callback_job is None:
    fail(".github/workflows/ci.yml: missing notify-dependabot-automerge callback job")
elif (
    workflow_job_permissions("notify-dependabot-automerge").strip() != "actions: write"
    or "needs: validate" not in callback_job
    or "github.actor == 'github-actions[bot]'" not in callback_job
    or "startsWith(github.ref_name, 'dependabot/')" not in callback_job
    or "Verify CI runner" not in callback_job
    or "gh workflow run auto-merge-dependabot.yml" not in callback_job
    or "actions/checkout" in callback_job
):
    fail(".github/workflows/ci.yml: Dependabot callback must stay branch-gated, checkout-free and actions:write-only")


# LocalSingleNode: a peer target with strict provenance and loopback-only services.
single = "Deployment/LocalSingleNode"
for path in ("compose/docker-compose.yml", "AgentSetup.md", "Scripts/bootstrap-node.sh", "Scripts/setup-status.sh", "Scripts/setup-next-step.sh", "Scripts/doctor.sh", "Scripts/run-maintenance.sh", "Scripts/restart-public-connector-check.sh", "Scripts/verify-release-identity.sh", "Scripts/prune-release-artifacts.sh", "Scripts/Tests/test-verify-release-identity.sh", "Scripts/Tests/test_prune_release_artifacts.py", "ansible/playbooks/PrepareSingleNode.yml", "ansible/playbooks/site.yml"):
    require_file(single + "/" + path)
single_compose = read(single + "/compose/docker-compose.yml")
for binding in re.findall(r'(?m)^      - "([^"\n]+:[0-9${}A-Z_]+)"$', single_compose):
    if not binding.startswith("127.0.0.1:"):
        fail("localsinglenode: published ports must bind loopback")
if single_compose.count('"127.0.0.1:') != 3:
    fail("localsinglenode: all three service publications must bind loopback")
require_contains(single + "/compose/docker-compose.yml", 'LocalAccounts__Enabled: "false"', "deployment account seeding disabled")
require_contains(single + "/ansible/templates/app.env.j2", "DataProtection__KeyEncryptionCertificatePath=/run/secrets/data-protection.pem", "single-node app certificate path")
require_contains(single + "/ansible/templates/app.env.j2", "DataProtection__KeyEncryptionCertificatePassword={{ vault_data_protection_certificate_password }}", "single-node protected certificate passphrase")
require_contains(single + "/ansible/templates/app.env.j2", "DataProtection__LegacyKeyStore={{ data_protection_legacy_key_store | default('None') }}", "single-node legacy Data Protection source selection")
require_contains(single + "/ansible/templates/app.env.j2", "DataProtection__LegacyRedisKey={{ data_protection_legacy_redis_key | default('') }}", "single-node legacy Redis key")
require_contains(single + "/ansible/templates/compose.env.j2", "DATA_PROTECTION_CERT_GID={{ data_protection_certificate_gid }}", "single-node certificate reader group")
require_contains(single + "/ansible/templates/compose.env.j2", "DATA_PROTECTION_LEGACY_HOST_PATH=/etc/{{ app_name }}/data-protection/legacy", "single-node legacy source bind path")
require_contains(single + "/compose/docker-compose.yml", "target: /run/secrets/data-protection.pem", "single-node read-only certificate mount")
require_contains(single + "/compose/docker-compose.yml", "target: /run/legacy-data-protection", "single-node legacy source mount")
require_contains(single + "/compose/docker-compose.yml", "read_only: true", "single-node read-only certificate mount")
require_contains(single + "/Scripts/lib/backup.py", "data-protection.pem", "single-node backup preserves app certificate recovery key")
require_contains(single + "/ansible/roles/single_node_stack/tasks/main.yml", "/data-protection/legacy", "single-node legacy source directory")
for needle in ("find-successful-ci-run.py", "--target-sha \"$TARGET_SHA\"", "--read-final-payload-receipt", "validate_release_manifest.py", "release_image_digest", "with-deploy-lock.sh", "git merge-base --is-ancestor", "git show \"${TARGET_SHA}:frontend-profile.txt\"", "--legacy-blazor-default", "TARGET_PROFILE_FILE_PRESENT=${profile_file_present}", 'if [[ "$RELEASE_MANIFEST_SCHEMA_VERSION" == 2 && "$TARGET_PROFILE_FILE_PRESENT" != true ]]', "--expected-frontend-profile \"$FRONTEND_PROFILE\"", "--expected-acceptance-profile \"$ACCEPTANCE_PROFILE\"", "--image-labels-json \"$IMAGE_LABELS_PATH\"", "--expected-ci-run-attempt", "verify-release-identity.sh \"$APP_IMAGE\" \"$RELEASE_IMAGE_DIGEST\" \"$FRONTEND_PROFILE\" \"$ACCEPTANCE_PROFILE\" \"$TARGET_SHA\" \"$RELEASE_MANIFEST_SCHEMA_VERSION\" \"$CI_RUN_ID\" \"$CI_RUN_ATTEMPT\" \"$SOURCE_REPO_URL\"", "LOCALSINGLENODE_HOST", "TARGET: localsinglenode", "release_frontend_profile=$FRONTEND_PROFILE", "release_acceptance_profile=$ACCEPTANCE_PROFILE"):
    require_contains(".github/workflows/cd-localsinglenode.yml", needle, "strict single-node release contract")

instance_resolver = read(single + "/Scripts/resolve-app-instance.py")
for needle, why in [
    ('instance not in ("primary", "additional")', "closed instance selector"),
    ('set(config) != {"schema_version", "frontend_profile", "settings", "public"}', "protected instance schema"),
    ('profile == selected_profile', "additional frontend distinct from primary"),
    ('roots must be disjoint', "cross-app directory rejection"),
    ('additional service ports overlap', "cross-app port rejection"),
    ('additional subnet overlaps', "cross-app subnet rejection"),
    ('verify_owned(config', "native ownership binding before deployment"),
    ('additional instance requires its own protected GitHub environment', "secret environment isolation"),
    ('os.O_EXCL | os.O_NOFOLLOW', "protected temporary files without overwrite"),
    ('"-" + profile.lower()', "distinct additional release names"),
]:
    if needle not in instance_resolver:
        fail(f"{single}/Scripts/resolve-app-instance.py: missing {why}")
instance_cd = normalize_workflow_text(read(".github/workflows/cd-localsinglenode.yml"))
for needle in ("default: primary", "vars.LOCALSINGLENODE_ADDITIONAL_ENVIRONMENT", "secrets.LOCALSINGLENODE_APP_INSTANCE",
               "python3 Deployment/LocalSingleNode/Scripts/resolve-app-instance.py", '-e @"$INSTANCE_EXTRA_VARS_FILE"',
               'export PUBLIC_HOSTNAME="$INSTANCE_PUBLIC_HOSTNAME"', '"$RUNNER_TEMP/instance-settings.yml"', '"$RUNNER_TEMP/instance-vars.json"'):
    if needle not in instance_cd:
        fail(f".github/workflows/cd-localsinglenode.yml: missing app isolation {needle}")
if instance_cd.find("resolve-app-instance.py") > instance_cd.find("Select and retrieve release payload under shared deployment lock"):
    fail(".github/workflows/cd-localsinglenode.yml: validate instance identity before downloading release inputs")
single_selection = workflow_step_text(instance_cd, "Select and retrieve release payload under shared deployment lock")
for needle, why in [
    ("with-deploy-lock.sh", "release selection uses the shared deployment lock"),
    ("find-successful-ci-run.py", "receipt selector is invoked"),
    ('--target-sha "$TARGET_SHA"', "selector binds the requested target SHA"),
    ("--read-final-payload-receipt", "GHCR selection requires a run-bound final receipt"),
    ('--payload-app-image-prefix "$RELEASE_PAYLOAD_PREFIX"', "receipt selection uses the configured payload package prefix"),
    ("pull_release_payload.py", "GHCR payload is pulled and validated by digest"),
    ('--payload-image-prefix "$RELEASE_PAYLOAD_PREFIX"', "GHCR payload pull uses the configured package prefix"),
    ("pin_release_payload.py", "validated GHCR payload is retained as an offline local pin"),
    ("import_legacy_release_payload.py", "legacy artifact is selected by exact attempt and verified archive digest"),
    ('--root "${DEPLOY_ROOT}/release-payloads/${GITHUB_REPOSITORY//\\//-}"', "local pin root is scoped to the configured deployment and repository"),
    ('--artifact-name "$MIGRATION_ARTIFACT_NAME"', "legacy artifact fallback uses the configured name"),
    ('RELEASE_PAYLOAD_TRANSPORT="ghcr-container"', "GHCR transport is frozen for new receipts"),
    ('RELEASE_PAYLOAD_TRANSPORT="actions-artifact"', "legacy transport is explicit for older runs"),
    ("--restore \"$pin_dir\"", "local-pin recovery restores the named immutable pin"),
    ('RELEASE_PAYLOAD_TRANSPORT="local-pin"', "local restore is identified to Ansible"),
    ("without Actions or GHCR payload access", "offline restore is summarized as an offline path"),
]:
    if needle not in single_selection:
        fail(f".github/workflows/cd-localsinglenode.yml: missing locked artifact selection behavior: {why}")
for needle, why in [
    ("local_payload_pin_key:", "manual dispatch accepts an exact local pin key"),
    ("if: inputs.local_payload_pin_key == ''", "local-pin recovery skips GHCR login"),
    ("release_payload_transport=$RELEASE_PAYLOAD_TRANSPORT", "Ansible receives the frozen payload transport"),
]:
    if needle not in instance_cd:
        fail(f".github/workflows/cd-localsinglenode.yml: missing {why}")
single_instance_resolver = read("Deployment/LocalSingleNode/Scripts/resolve-app-instance.py")
if '"DEPLOY_ROOT": config["deploy_root"]' not in single_instance_resolver:
    fail("Deployment/LocalSingleNode/Scripts/resolve-app-instance.py: selected instance deploy root must be exported for local payload pins")
if "actions/download-artifact@" in instance_cd:
    fail(".github/workflows/cd-localsinglenode.yml: release artifact selection and download must share the host lock")
single_stack = read(single + "/ansible/roles/single_node_stack/tasks/main.yml")
for needle, why in [
    ("when: (release_payload_transport | default('ghcr-container')) != 'local-pin'", "local-pin recovery skips the network image pull"),
    ("--pull never", "local-pin recovery starts the cached exact image without pulling"),
    ("app_image_ref in ((staged_image.stdout | from_json)[0].RepoDigests | default([]))", "cached local image must match the pinned digest"),
    ("release_payload_pin_key", "single-node release marker retains its exact local pin key"),
    ("release-state/previous.json", "previous single-node release remains available for recovery"),
]:
    if needle not in single_stack:
        fail(f"Deployment/LocalSingleNode/ansible/roles/single_node_stack/tasks/main.yml: missing {why}")
for path, why in [
    ("Deployment/LocalCluster/Scripts/prune-migration-artifacts.sh", "LocalCluster local pin retention runs under the artifact maintenance owner"),
    (single + "/Scripts/prune-release-artifacts.sh", "LocalSingleNode local pin retention runs under the artifact maintenance owner"),
]:
    for needle in ("pin_release_payload.py", "--prune-root", "--current-marker", "--recovery-marker", "--max-candidates-per-profile 3", "--max-unprotected-bytes 1073741824", "--apply"):
        require_contains(path, needle, why)
    if read(path).count("pin_release_payload.py") < 2:
        fail(f"{path}: local pin cleanup must print a dry-run preview before applying retention")
for path, needle in [
    (".github/workflows/cd-localcluster.yml", '-e "release_payload_pin_key=${RELEASE_PAYLOAD_PIN_KEY}"'),
    (".github/workflows/cd-localsinglenode.yml", '-e "release_payload_pin_key=$RELEASE_PAYLOAD_PIN_KEY"'),
]:
    require_contains(path, needle, "selected immutable pin key is passed into the deployed release marker")

single_maintenance = read(".github/workflows/localsinglenode-maintenance.yml")
single_artifact_job = single_maintenance.split("  prune-release-artifacts:", 1)[-1]
single_maintenance_job = single_maintenance.split("  maintenance:", 1)[-1].split("  prune-release-artifacts:", 1)[0]
single_dispatch = single_maintenance.split("  workflow_dispatch:", 1)[-1].split("  schedule:", 1)[0]
for needle, why in [
    ("\n      artifact_only:\n", "artifact-only dispatch input"),
    ("\n      apply_artifacts:\n", "manual artifact-apply input"),
    ("default: false", "default-off artifact preview and apply inputs"),
]:
    if needle not in single_dispatch:
        fail(f".github/workflows/localsinglenode-maintenance.yml: missing {why}")
if "if: github.event_name == 'workflow_dispatch' && inputs.artifact_only != true" not in single_maintenance_job:
    fail(".github/workflows/localsinglenode-maintenance.yml: app maintenance must be skipped for artifact-only dispatches and schedules")
if "ACTIONS_ARTIFACT_RETENTION_ENABLED: ${{ (github.event.schedule == '17 3 * * *' || github.event.schedule == '27 3 * * *' || (github.event_name == 'workflow_dispatch' && inputs.apply_artifacts == true)) && (vars.ACTIONS_ARTIFACT_RETENTION_ENABLED || 'false') }}" not in single_artifact_job:
    fail(".github/workflows/localsinglenode-maintenance.yml: manual artifact deletion must require apply_artifacts=true and the repository retention variable")
for needle, why in [
    ('cron: "17 3 * * *"', "daily primary artifact retention schedule"),
    ('cron: "27 3 * * *"', "daily additional-app artifact retention schedule"),
    ("prune-release-artifacts:", "artifact retention job"),
    ("template-artifact-retention", "retention concurrency group"),
    ("actions: write", "permission to delete old artifacts"),
    ("ci_report_store.py prune", "bounded local CI report retention"),
    ("with-deploy-lock.sh python3 Scripts/CI/ci_report_store.py prune", "local CI report pruning under the deployment lock"),
    ("ci_report_store.py prune --repository \"$GITHUB_REPOSITORY\" --dry-run", "dry-run local report retention"),
    ("Preview local CI report retention under the shared deployment lock", "report retention preview step"),
    ("bash Deployment/Common/Scripts/with-deploy-lock.sh bash Deployment/LocalSingleNode/Scripts/prune-release-artifacts.sh", "artifact pruning under the deployment lock"),
    ("github.event.schedule == '27 3 * * *'", "additional-app schedule selects its protected environment"),
    ("Require green main CI for unchanged operation code", "verified operation source"),
    ("verify-operation-source.py", "green CI source gate"),
    ("prune_archived_diagnostics:", "off-by-default archived diagnostic cleanup input"),
    ("inputs.prune_archived_diagnostics == true", "manual-only archived diagnostic deletion"),
    ("prune-archived-diagnostic-artifacts.py", "manifest-bound diagnostic artifact cleanup"),
    ("Plans/ZeroCostDiagnosticArchiveManifest-20261017.json", "exact preserved archive manifest"),
    ("with-deploy-lock.sh", "archived diagnostic cleanup under shared deployment lock"),
]:
    if needle not in single_maintenance:
        fail(f".github/workflows/localsinglenode-maintenance.yml: missing {why}")
for needle, why in [
    ("Require main branch", "main-ref-only pruning"),
    ("Require green main CI for unchanged operation code", "verified operation source"),
    ("verify-operation-source.py", "green CI source gate"),
]:
    if needle not in single_artifact_job:
        fail(f".github/workflows/localsinglenode-maintenance.yml: missing {why} in the artifact job")
single_pruner = read(single + "/Scripts/prune-release-artifacts.sh")
for needle, why in [
    ("--keep 0", "retire unprotected legacy migration artifacts after the GHCR cutover"),
    ("read_release_acceptance.py", "exact current and recovery release identity protection"),
    ("--ci-run-id", "accepted CI run identity"),
    ("--expected-source-repo-url", "release marker repository binding"),
    ('"$deploy_root/release-state/previous.json"', "exact recovery release marker identity"),
    ("--deployment-workflow-file cd-localcluster.yml", "LocalCluster recovery history protection"),
    ("--deployment-workflow-file cd-localsinglenode.yml", "LocalSingleNode recovery history protection"),
    ('--protect-run-id "$live_run_id"', "exact current release artifact protection"),
    ('--protect-run-id "$recovery_run_id"', "exact recovery release artifact protection"),
]:
    if needle not in single_pruner:
        fail(f"{single}/Scripts/prune-release-artifacts.sh: missing {why}")
single_pruner_tests = read(single + "/Scripts/Tests/test_prune_release_artifacts.py")
if "test_pruner_protects_current_and_recovery_ci_runs" not in single_pruner_tests:
    fail(f"{single}/Scripts/Tests/test_prune_release_artifacts.py: missing current/recovery artifact protection regression test")
artifact_pruner = read("Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py")
for needle, why in [
    ("workflow_dispatch_input_names(", "legacy deployment recovery accepts only understood dispatch inputs"),
    ("workflow_job_step(", "legacy deployment SHA proof is scoped to the deploy job's named steps"),
    ("legacy_dispatch_head_sha(", "fixed-title deployments require their own workflow source to prove GITHUB_SHA targeting"),
    ("head_repository.get(\"full_name\") != repo", "legacy workflow content must come from the deployment repository"),
    ("input_names.issubset({\"run_migrations\"})", "legacy fallback rejects alternate target inputs"),
]:
    if needle not in artifact_pruner:
        fail(f"Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py: missing {why}")
artifact_pruner_tests = read("Deployment/Common/Scripts/Tests/test_prune_actions_artifacts.py")
for needle, why in [
    ("test_legacy_fixed_title_uses_head_sha_only_when_historical_workflow_binds_it", "historical target resolution regression test"),
    ("test_legacy_fixed_title_with_target_sha_input_fails_closed", "target override rejection regression test"),
    ("test_legacy_fixed_title_without_head_binding_fails_closed", "missing binding rejection regression test"),
    ("test_legacy_fixed_title_ignores_matching_lines_outside_deploy_job", "other-job source lines rejection regression test"),
]:
    if needle not in artifact_pruner_tests:
        fail(f"Deployment/Common/Scripts/Tests/test_prune_actions_artifacts.py: missing {why}")
for role in ("single_node_stack", "single_node_public"):
    require_contains(single + f"/ansible/roles/{role}/tasks/main.yml", "LOCALSINGLENODE_SETTINGS_FILE: \"{{ instance_settings_file | default('') }}\"", "collision check uses selected instance settings through privilege elevation")
require_contains(single + "/Scripts/lib/ls_settings.py", 'os.environ.get("LOCALSINGLENODE_SETTINGS_FILE")', "selected instance settings shared by runtime verification and acceptance")
require_file(single + "/Scripts/Tests/test_app_instance.py")

setup_workflow = read(".github/workflows/localsinglenode-app-setup.yml")
for needle in ("test \"$GITHUB_REF\" = refs/heads/main", "verify-operation-source.py", "fetch-depth: 0", "--prepare-additional",
               "vars.LOCALSINGLENODE_RUNNER_LABEL", "with-deploy-lock.sh", "prepare-additional-app.sh", "if: always()"):
    if needle not in setup_workflow:
        fail(f".github/workflows/localsinglenode-app-setup.yml: missing scoped setup guard {needle}")
scoped_setup = read(single + "/ansible/playbooks/PrepareAdditionalApp.yml")
for needle in ("verify-additional-app.py", "check-port-collisions.sh", "--settings-file", "backup_existing_host: true",
               "force: false", '"/etc/{{ app_name }}/settings.yml"', "single_node_backup", "ufw allow from {{ lan_cidr }} to any port {{ lan_http_port }}"):
    if needle not in scoped_setup:
        fail(f"{single}/ansible/playbooks/PrepareAdditionalApp.yml: missing owned-app setup {needle}")
for needle in ("mint_base", "caddy_install", "single_node_firewall", "avahi", "state: restarted", "ansible.builtin.user", "ansible.builtin.apt", "sudoers"):
    if needle in scoped_setup:
        fail(f"{single}/ansible/playbooks/PrepareAdditionalApp.yml: app setup cannot change shared host configuration {needle}")
scoped_wrapper = read(single + "/Scripts/prepare-additional-app.sh")
for needle in ("LOCALCLUSTER_DEPLOY_LOCK_TOKEN", "env -u LOCALSINGLENODE_SETTINGS_FILE", "native-readiness.py", "PrepareAdditionalApp.yml"):
    if needle not in scoped_wrapper:
        fail(f"{single}/Scripts/prepare-additional-app.sh: missing lock/readiness scope {needle}")
if scoped_wrapper.find("native-readiness.py") > scoped_wrapper.find("ansible-playbook"):
    fail("localsinglenode: recheck existing workload, backup and capacity before scoped preparation")
resource_guard = read(single + "/Scripts/verify-additional-app.py")
for needle in ("instance.verify_owned(primary, source)", "instance.verify_owned(candidate, source)", "root.parents", "inspect_resources",
               'for kind in ("network", "volume")', "unowned backup unit", "os.geteuid() != 0"):
    if needle not in resource_guard:
        fail(f"{single}/Scripts/verify-additional-app.py: missing foreign-resource rejection {needle}")
backup_tasks = read(single + "/ansible/roles/single_node_backup/tasks/main.yml")
if backup_tasks.count("when: not (backup_existing_host | default(false) | bool)") != 3:
    fail("localsinglenode: app-only backup preparation must skip deploy group and shared reboot-helper changes")
require_contains(single + "/Scripts/validate-playbooks.sh", "PrepareSingleNode PrepareAdditionalApp site", "scoped app playbook syntax coverage")
require_file(single + "/Scripts/Tests/test_additional_setup.py")

public_publisher = read(single + "/Scripts/configure-public-deployment.py")
for needle in ("--environment", "--instance-config-file", "module.validate_additional", "configured distinct repository environment",
               '"LOCALSINGLENODE_APP_INSTANCE"', '"--env", args.environment', "input_value=json.dumps(payload, sort_keys=True)"):
    if needle not in public_publisher:
        fail(f"{single}/Scripts/configure-public-deployment.py: missing additional public secret isolation {needle}")
require_file(single + "/Scripts/Tests/test_public_instance.py")

single_release_identity = read(single + "/Scripts/verify-release-identity.sh")
for needle, why in [
    ("com.blazorautoapp.frontend-profile", "running frontend profile identity"),
    ("com.blazorautoapp.acceptance-profile", "running acceptance profile identity"),
    ("org.opencontainers.image.revision", "running source revision identity"),
    ("schema v1 is supported only for BlazorAuto", "legacy Blazor-only identity rule"),
]:
    if needle not in single_release_identity:
        fail(f"{single}/Scripts/verify-release-identity.sh: missing {why}")
for needle, why in [
    ("Require staged release identity before migration or replacement", "pre-migration image identity check"),
    ("com.blazorautoapp.frontend-profile", "staged frontend profile identity"),
    ("com.blazorautoapp.acceptance-profile", "staged acceptance profile identity"),
    ("org.opencontainers.image.revision", "staged source revision identity"),
]:
    if needle not in read(single + "/ansible/roles/single_node_stack/tasks/main.yml"):
        fail(f"{single}/ansible/roles/single_node_stack/tasks/main.yml: missing {why}")
for needle in [
    "Render protected Compose interpolation allowlist",
    "docker compose --env-file .compose.env up -d postgres redis",
    "docker compose --env-file .compose.env stop web",
]:
    if needle not in read(single + "/ansible/roles/single_node_stack/tasks/main.yml"):
        fail(f"{single}/ansible/roles/single_node_stack/tasks/main.yml: missing Compose environment isolation {needle}")
if "bash Deployment/LocalSingleNode/Scripts/Tests/test-verify-release-identity.sh" not in ci:
    fail(".github/workflows/ci.yml: LocalSingleNode release identity fixtures must run in CI")
for path in (".github/workflows/cd-localsinglenode.yml", ".github/workflows/localsinglenode-maintenance.yml"):
    workflow = read(path)
    if "vars.LOCALSINGLENODE_HOST" not in workflow or "test -n" not in workflow or "'localsinglenode-books'" not in workflow:
        fail("localsinglenode: workflow needs explicit host and app runner label")
require_contains(".github/workflows/localsinglenode-maintenance.yml", "ACTIONS_ARTIFACT_RETENTION_ENABLED", "default-off single-node artifact deletion gate")
for path in (ROOT / single).rglob("*"):
    if not path.is_file() or "__pycache__" in path.parts:
        continue
    content = path.read_text(encoding="utf-8-sig")
    if re.search(r"docker\s+(?:volume|system)\s+prune", content):
        fail("localsinglenode: volume/system prune is forbidden")
    for address in re.findall(r"(?<![0-9.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9.])", content):
        if address != "127.0.0.1" and not address.startswith(("172.30.", "192.0.2.")):
            fail(f"localsinglenode: unsupported tracked IPv4 literal {address} in {path.relative_to(ROOT)}")
require_contains(".gitignore", "Deployment/LocalSingleNode/machine.yml", "ignored detected node facts")
require_contains("Deployment/Common/Scripts/install-ansible.sh", "USER_ONLY", "unprivileged install-user provisioning")
require_contains("Deployment/LocalCluster/Scripts/ci-docker-smoke.sh", "Scripts/Test-DeployedSite.ps1", "profile-aware HTTP acceptance in CI")
smoke = read("Deployment/LocalCluster/Scripts/ci-docker-smoke.sh")
for needle, why in [
    ('FRONTEND_PROFILE="${FRONTEND_PROFILE:-BlazorAuto}"', "container smoke defaults to the persisted template profile"),
    ('if [[ "$FRONTEND_PROFILE" == "React" ]]; then', "React image has a separate public-only smoke path"),
    ("command -v node", "final image smoke rejects a Node runtime"),
    ('/books/author/example', "React image smoke covers direct detail navigation"),
    ('/api/author-books', "React image smoke reads the public seeded catalog"),
    ('^Cache-Control:[[:space:]]*public, ?max-age=31536000, ?immutable', "React image smoke verifies immutable fingerprinted assets"),
    ('^Cache-Control:[[:space:]]*private, ?no-store', "React image smoke verifies private API cache denial"),
    ('/api/client-config', "React image smoke reads explicit capability before account-route expectations"),
    ('payload["accountsEnabled"]', "React image smoke validates the account capability"),
    ('if [[ "$accounts_enabled" == "true" ]]; then', "React image smoke selects enabled versus disabled route expectations"),
    ("Allow:[[:space:]]*POST", "React image smoke verifies enabled POST-only reads return 405"),
    ('/api/auth/not-a-real-operation', "React image smoke verifies unknown enabled routes remain 404"),
    ('inactive_paths=(/Account /api/auth/not-a-real-operation /assets/missing.js)', "React image smoke verifies unknown API, React-only and missing paths stay 404"),
    ('test ! -e /app/wwwroot/_framework && test ! -e /app/wwwroot/_content', "React image smoke rejects inactive Blazor assets"),
    ('test ! -e /app/wwwroot/index.html && test ! -e /app/wwwroot/assets', "Blazor image smoke rejects inactive React assets"),
]:
    if needle not in smoke:
        fail(f"Deployment/LocalCluster/Scripts/ci-docker-smoke.sh: missing {why}")
react_smoke_start = smoke.index('if [[ "$FRONTEND_PROFILE" == "React" ]]; then')
react_smoke_end = smoke.index("\nelse\n", react_smoke_start)
react_smoke = smoke[react_smoke_start:react_smoke_end]
if "Test-DeployedSite.ps1" not in react_smoke or '-AcceptanceProfile "$FRONTEND_ACCEPTANCE_PROFILE"' not in react_smoke:
    fail("React Docker smoke must run ReactPublicV1 HTTP acceptance")
for needle, why in [
    ("Category=ReactPackagedDisabled", "disabled packaged React browser filter"),
    ("Category=ReactPackagedEnabled", "enabled packaged React account browser filter"),
]:
    if needle not in smoke:
        fail(f"React Docker smoke: missing {why}")
for needle, why in [
    ("$REACT_DISABLED_BROWSER_FILTER", "React Docker smoke runs disabled packaged browser acceptance"),
    ("$REACT_ENABLED_BROWSER_FILTER", "React Docker smoke runs enabled packaged account browser acceptance"),
    ("Packaged React disabled browser journey", "disabled packaged browser suite rejects skipped tests"),
    ("Packaged React enabled account browser journey", "enabled packaged account browser suite rejects skipped tests"),
    ("--expected-skipped 0", "React packaged browser suites reject skipped tests"),
]:
    if needle not in react_smoke:
        fail(f"React Docker smoke: missing {why}")
if any(needle in react_smoke for needle in ("BROWSER_SMOKE_FILTER", "Category=BlazorAuto", "Category=Blazor")):
    fail("React Docker smoke must not run Blazor browser/account acceptance")
deployed_site_acceptance = read("Scripts/Test-DeployedSite.ps1")
for needle, why in [
    ("[ValidateSet('BlazorAuto', 'React')]", "validated frontend acceptance input"),
    ("[ValidateSet('BlazorAutoV1', 'ReactPublicV1')]", "validated acceptance contract input"),
    ("FrontendProfile and AcceptanceProfile do not match", "mismatched profile pair fails before network access"),
    ("function Invoke-ReactPublicAcceptance", "separate React public-only acceptance branch"),
    ("function Get-ReactCapability", "explicit React capability discovery"),
    ("/api/client-config", "capability endpoint checked before profile acceptance"),
    ("function Invoke-ReactAccountSessionAcceptance", "enabled React anonymous session acceptance"),
    ("function Invoke-BlazorAccountAcceptance", "preserved Blazor account acceptance branch"),
    ("React-no-cookie", "React acceptance proves no session cookie was created"),
    ("RequestMethod 'HEAD'", "React acceptance includes safe HEAD checks"),
    ("React-enabled-session-cache", "enabled account session is private and no-store"),
    ("React-enabled-session-cookie", "enabled anonymous session does not issue an authentication cookie"),
]:
    if needle not in deployed_site_acceptance:
        fail(f"Scripts/Test-DeployedSite.ps1: missing {why}")
react_acceptance_start = deployed_site_acceptance.index("function Invoke-ReactPublicAcceptance")
react_acceptance_end = deployed_site_acceptance.index("function Invoke-BlazorAccountAcceptance", react_acceptance_start)
react_acceptance = deployed_site_acceptance[react_acceptance_start:react_acceptance_end]
for needle, why in [
    ("React-enabled-post-only-GET", "enabled POST-only GET rejection"),
    ("React-enabled-post-only-HEAD", "enabled POST-only HEAD rejection"),
    ("React-enabled-unknown-api", "unknown enabled API route remains a 404"),
    ("/api/auth/not-a-real-operation", "explicit unknown API route probe"),
    ("/assets/missing.js", "missing React asset remains a 404"),
]:
    if needle not in react_acceptance:
        fail(f"Scripts/Test-DeployedSite.ps1: React acceptance lacks {why}")
capability_request = deployed_site_acceptance.index("$capability = Get-ReactCapability")
common_request = deployed_site_acceptance.index("Invoke-CommonAcceptance $anonymous $FrontendProfile", capability_request)
if capability_request > common_request:
    fail("React acceptance must read explicit capability before common or profile checks")
if "Form " in react_acceptance or "Login " in react_acceptance or "RequestMethod 'POST'" in react_acceptance:
    fail("React public HTTP acceptance must not submit forms or credentials")
require_contains(single + "/Scripts/lib/platform_check.py", '"WSL_DISTRO_NAME"', "native deployment boundary")
require_contains(single + "/Scripts/lib/doctor.py", '"ip", "-j", "-4", "address", "show"', "mDNS check discovers the interface owning the deployment IPv4")
require_contains(single + "/Scripts/lib/doctor.py", '"ResolveHostName", "iisiu", str(index), "0", name, "0", "0"', "mDNS check resolves the deployment name on its LAN interface")
require_contains(single + "/Scripts/lib/doctor.py", 'data[4] == machine["ip"]', "mDNS check requires the exact deployment IPv4")
require_contains(single + "/Scripts/lib/doctor.py", '"--property=Id,ActiveState,User,WorkingDirectory"', "read-only runner service inspection without deploy home access")
require_contains(single + "/Scripts/lib/collisions.py", 'recorded_source.casefold() == source.casefold()', "case-insensitive GitHub repository ownership with exact app roots")
require_contains(single + "/Scripts/lib/collisions.py", '(network.get("IPAM") or {}).get("Config") or []', "nullable built-in Docker network IPAM while checking foreign subnets")
require_contains(single + "/Scripts/lib/collisions.py", 'config = settings(settings_file)', "candidate collision settings use the normal parser and validation")
require_contains(single + "/Scripts/lib/collisions.py", 'parser.add_argument("--settings-file", type=Path)', "explicit read-only candidate settings file")
require_contains(".github/workflows/localsinglenode-readiness.yml", 'secrets.LOCALSINGLENODE_READINESS_CANDIDATE', "private candidate data is masked in runner logs")
require_contains(single + "/Scripts/native-readiness.py", "collisions.check(payload['source_repo_url'], settings_file=path)", "candidate inspection preserves the normal non-bootstrap collision gate")
require_contains(single + "/Scripts/acceptance-check.sh", 'lib/readiness.py', "bounded LAN warmup before the unchanged full acceptance check")
require_contains(single + "/Scripts/acceptance-check.sh", '-FrontendProfile "$FRONTEND_PROFILE" -AcceptanceProfile "$ACCEPTANCE_PROFILE"', "LAN acceptance uses trusted release profiles")
require_contains(single + "/Scripts/lib/acceptance_profile.sh", "read_release_acceptance.py", "standalone node acceptance reads the deployed release marker")
require_contains(single + "/Scripts/lib/acceptance_profile.sh", "Both FRONTEND_PROFILE and ACCEPTANCE_PROFILE are required together.", "acceptance profile input must be a complete pair")
require_contains(single + "/Scripts/lib/readiness.py", 'timeout=180', "180-second LAN readiness deadline")
require_contains(single + "/Scripts/run-maintenance.sh", '--report-fresh-since "$requested"', "requested backups prove fresh completion before maintenance")
require_contains(".github/workflows/localsinglenode-maintenance.yml", "restart_connector:", "opt-in connector restart recovery")
require_contains(".github/workflows/localsinglenode-maintenance.yml", "inputs.restart_connector == true", "connector restart requires explicit opt-in")
require_contains(".github/workflows/localsinglenode-maintenance.yml", "RESTART_CONNECTOR", "connector restart is validated against acceptance-only mode")
require_contains(".github/workflows/localsinglenode-maintenance.yml", "Scripts/restart-public-connector-check.sh", "connector restart invokes the scoped recovery check")
require_contains(single + "/Scripts/restart-public-connector-check.sh", 'sudo -n systemctl restart "$UNIT"', "connector restart is non-interactive and scoped to the app unit")
require_contains(single + "/Scripts/restart-public-connector-check.sh", "InvocationID", "connector recovery proves a new systemd invocation")
for needle in ("app_instance:", "inputs.app_instance", "vars.LOCALSINGLENODE_ADDITIONAL_ENVIRONMENT",
               "secrets.LOCALSINGLENODE_APP_INSTANCE", "resolve-app-instance.py", "Require green main CI for unchanged operation code",
               "restart_app:", "inputs.restart_app == true", "Scripts/restart-app-check.py", "with-deploy-lock.sh",
               "Additional-app maintenance cannot request a shared host reboot", "if: always()", "instance-settings.yml"):
    require_contains(".github/workflows/localsinglenode-maintenance.yml", needle, "protected per-app maintenance and scoped restart")
for needle in ("instance.verify_owned(config, source)", "verify-release-identity.sh", "LOCALCLUSTER_DEPLOY_LOCK_TOKEN",
               "'--project-name', app, 'ps', '-q'", "'--project-name', config['app_name'], 'restart', '--no-deps', 'web'",
               "CHECK_PHASE = 'primary sibling inventory'", "catalog(config) != seed", "containers(primary) != sibling", "'mounts', 'restarts'"):
    require_contains(single + "/Scripts/restart-app-check.py", needle, "owned app persistence and sibling protection")
require_contains(single + "/Scripts/lib/doctor.py", "runner_active(runner_app())", "additional app reuses primary runner")
require_contains(single + "/Scripts/lib/maintenance.py", 'runner_app()', "runner residue uses the existing primary registration")
require_file(single + "/Scripts/Tests/test_app_operations.py")
for needle in ("--first-parent", "--no-renames", "100644", "ordinary_documentation", "no_eligible_run", "cat-file", "decode('utf-8')",
               "validated_code_sha", "--is-shallow-repository", "find-successful-ci-run.py"):
    require_contains("Deployment/Common/Scripts/verify-operation-source.py", needle, "strict unchanged-code operational CI gate")
require_file("Deployment/Common/Scripts/Tests/test_operation_source.py")
require_contains(single + "/Scripts/lib/backup.py", 'completed < started', "requested backups cannot reuse stale completion markers")
require_contains(single + "/Scripts/lib/backup.py", 'Fresh protected backup:', "explicit fresh dump evidence without secret contents")
require_contains(single + "/Scripts/acceptance-check.sh", 'public-acceptance-check.sh', "public acceptance after LAN acceptance")
require_contains(single + "/Scripts/lib/readiness.py", 'response.read(64).strip() == b"Healthy"', "readiness rejects empty HTTP 200")
require_contains(single + "/Scripts/public-acceptance-check.sh", '-FrontendProfile "$FRONTEND_PROFILE" -AcceptanceProfile "$ACCEPTANCE_PROFILE"', "public acceptance uses trusted release profiles")
require_contains(single + "/Scripts/public-acceptance-check.sh", '-BaseUrl "$PUBLIC_URL"', "configured public HTTPS acceptance")
require_contains(single + "/Scripts/lib/public_config.py", 'os.O_EXCL | os.O_NOFOLLOW', "protected public secret output")
require_contains(single + "/Scripts/lib/public_config.py", 'validate_connector_token(token, tunnel_id, expected_account_id)', "shared connector credential identity validation")
require_contains("Deployment/Common/Scripts/Component/lib/cloudflare_tunnel.py", 'claims.get("t") != tunnel_id', "matching connector credential identity")
require_contains(single + "/ansible/roles/single_node_public/templates/app.caddy.j2", 'bind 127.0.0.1', "loopback public ingress")
require_contains(single + "/ansible/roles/single_node_public/templates/app.caddy.j2", 'header_up X-Forwarded-Proto https', "public HTTPS scheme")
require_contains(single + "/ansible/roles/single_node_public/templates/cloudflared.service.j2", '--token-file %d/tunnel-token', "file-based connector credential")
require_contains(single + "/ansible/roles/single_node_public/templates/cloudflared.service.j2", 'LoadCredential=tunnel-token:', "systemd protected credential")
require_contains(single + "/ansible/roles/single_node_public/templates/cloudflared.service.j2", '/usr/local/libexec/cloudflared-{{ app_name }}/{{ public_cloudflared_version }}/cloudflared', "traversable app-specific connector executable")
require_not_contains(single + "/ansible/roles/single_node_public/templates/cloudflared.service.j2", '{{ deploy_root }}/cloudflared/', "connector executable outside private deploy root")
require_contains(single + "/ansible/roles/single_node_public/tasks/main.yml", 'checksum: "{{ public_cloudflared_checksum }}"', "checksum-pinned connector")
require_contains(single + "/ansible/roles/single_node_public/tasks/main.yml", "public_exec_base.stat.mode[-1] in ['1', '3', '5', '7']", "shared executable parent must permit dynamic-user traversal")
require_contains(single + "/ansible/roles/single_node_public/tasks/main.yml", '--property=ActiveState,SubState,ExecMainStatus', "bounded connector startup health check")
require_contains(single + "/ansible/roles/single_node_public/tasks/main.yml", "'ActiveState=active'", "connector must reach active systemd state")
require_contains(single + "/ansible/roles/single_node_public/tasks/main.yml", "'SubState=running'", "connector must be running before public acceptance")
require_contains(single + "/ansible/roles/single_node_public/tasks/main.yml", "'ExecMainStatus=0'", "connector process must have a successful exit status")
require_contains("Scripts/Test-DeployedSite.ps1", "@('http', 'https')", "HTTP and HTTPS acceptance")
require_contains("Scripts/Test-DeployedSite.ps1", "'HTTPS-cookie'", "public authentication cookie security")
for path, verify_name, acceptance_name in [
    (".github/workflows/cd-localcluster.yml", "Verify running release identity", "Run acceptance check"),
    (".github/workflows/cd-localsinglenode.yml", "Verify running release identity", "Run HTTP acceptance"),
]:
    workflow = read(path)
    if workflow.index(verify_name) > workflow.index(acceptance_name):
        fail(f"{path}: running image identity must be verified before profile-selected HTTP acceptance")
require_contains(".github/workflows/cd-localsinglenode.yml", '-e @"$PUBLIC_EXTRA_VARS_FILE"', "validated public inputs deployed")
require_contains(".github/workflows/cd-localsinglenode.yml", 'rm -f -- "$PUBLIC_EXTRA_VARS_FILE"', "temporary connector credential cleanup")
require_contains("Deployment/Common/Scripts/Component/lib/cloudflare_tunnel.py", 'Tunnel name exists without recorded ownership', "foreign tunnel refusal")
require_contains("Deployment/Common/Scripts/Component/lib/cloudflare_tunnel.py", 'replacement is refused', "foreign DNS refusal")
require_contains("Deployment/Common/Scripts/Component/lib/cloudflare_tunnel.py", 'current_result.get("config") is None', "unconfigured owned tunnel response handling")
require_contains("Deployment/Common/Scripts/Tests/test_cloudflare_tunnel.py", 'test_new_tunnel_null_configuration_is_initialized_once', "new tunnel null configuration regression")
require_contains("Deployment/Common/Scripts/Tests/test_cloudflare_tunnel.py", 'test_owned_null_configuration_read_only_check_never_mutates', "unconfigured tunnel read-only regression")
require_contains("Deployment/Common/Scripts/Tests/test_cloudflare_tunnel.py", 'test_malformed_owned_configuration_is_refused', "malformed tunnel configuration refusal regression")


for needle in ("protected_application_image_references", "protected_refs = protected_references()", "intersection(protected_refs)"):
    require_contains("Deployment/LocalSingleNode/Scripts/lib/maintenance.py", needle, "verified current/recovery and pending image protection")
require_contains("Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh", "protected-release-images.sh", "cluster image retention uses existing release status authority")
require_contains("Deployment/LocalCluster/Scripts/prune-docker-residue.sh", 'RELEASE_PROTECTION_VERIFIED', "standalone image cleanup defers without verified protection")
require_contains("Deployment/Common/Scripts/Component/lib/release_status.py", "verify_cached_application_image", "offline recovery verifies exact cached application image")
require_contains("Deployment/LocalCluster/Scripts/release-status.py", "application_image_inspector=verify_cluster_cached_application_image", "offline cluster recovery checks app nodes")
maintenance_step = read(".github/workflows/localsinglenode-maintenance.yml").split("- name: Protected backup and scoped maintenance", 1)[1].split("- name:", 1)[0]
for binding in ("GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}", "LOCALSINGLENODE_HOST: ${{ vars.LOCALSINGLENODE_HOST }}"):
    if binding not in maintenance_step:
        fail("Scoped maintenance must pass protected release-status inputs: " + binding.split(":", 1)[0])

if failures:
    print("Deployment audit failed:")
    for failure in failures:
        print(f" - {failure}")
    sys.exit(1)

print("Deployment audit passed.")
