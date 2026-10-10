#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


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
    "Deployment/LocalCluster/Scripts/verify-release-identity.sh",
    "Deployment/LocalCluster/Scripts/Tests/test-verify-release-identity.sh",
    "Scripts/CI/migration_staging_artifact.py",
    "Scripts/CI/tests/test_migration_staging_artifact.py",
    "Deployment/Common/Scripts/install-ansible.sh",
    "Deployment/Common/Scripts/prune-actions-artifacts.sh",
    "Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py",
    "Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py",
    "Deployment/Common/Scripts/read-release-setting.sh",
    "Deployment/Common/Scripts/validate-common-release.sh",
    "Deployment/Common/Scripts/Component/lib/read-release-setting.py",
    "Deployment/Common/Scripts/Component/lib/release_settings.py",
    "Deployment/Common/Scripts/Component/lib/simple_yaml.py",
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
    "Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py",
    "Deployment/LocalCluster/Scripts/Component/lib/generate-inventory.py",
    "Deployment/LocalCluster/Scripts/Component/lib/read-deploy-setting.py",
    "Deployment/LocalCluster/Scripts/Component/lib/validate-deploy-settings.py",
    "Deployment/LocalCluster/Scripts/Component/lib/validate-vault.py",
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
    "Deployment/LocalCluster/Scripts/verify-deployment.sh",
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
])
for file in required_files:
    require_file(file)


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


guide = read("Deployment/LocalCluster/HowToDeployLocalCluster.md")
if guide.count("```") % 2 != 0:
    fail("Deployment/LocalCluster/HowToDeployLocalCluster.md: unbalanced markdown code fences")

for forbidden in [
    ".deploy.local",
    "discover-node",
    "health-check",
    "Deployment/LocalCluster/compose/load-balancer",
    "Deployment/LocalCluster/caddy/sites/app.caddy",
    "Deployment/LocalCluster/inventory/prod/host_vars",
]:
    if forbidden in guide:
        fail(f"Deployment/LocalCluster/HowToDeployLocalCluster.md: contains stale deployment reference: {forbidden}")

for script_name in sorted(
    set(re.findall(r"(?:\./)?Deployment/LocalCluster/Scripts/([A-Za-z0-9_.-]+\.sh)", guide))
    | set(re.findall(r"`([A-Za-z0-9_.-]+\.sh)`", guide))
):
    if not exists(f"Deployment/LocalCluster/Scripts/{script_name}"):
        fail(
            "Deployment/LocalCluster/HowToDeployLocalCluster.md: "
            f"references missing script: Deployment/LocalCluster/Scripts/{script_name}"
        )

for needle, why in [
    ("## 4. Reserve LAN IPs", "dedicated router IP reservation step"),
    ("## 5. Generate Inventory", "dedicated control-machine inventory generation step"),
    ("Ensure all four nodes are using their reserved IPs before proceeding.", "router reservation checkpoint"),
    ("validate-machines.sh", "machines.yml validation checkpoint before inventory generation"),
    ("Success: prints OK lines for machines.yml, deployment settings, and all four nodes.", "machines validation success checkpoint"),
    ("Run this only from a full repository checkout on the control machine.", "verify-bootstrap full-checkout warning"),
    ("test -f \"$REPO_ROOT/Deployment/LocalCluster/Scripts/verify-bootstrap.sh\"", "verify-bootstrap dependency checkpoint"),
    ("## 12. Configure The GitHub CD Environment", "dedicated GitHub environment setup step"),
    ("New environment -> localcluster", "localcluster environment creation"),
    ("Deployment branches and tags: Selected branches and tags", "deployment branch restriction instructions"),
    ("Allowed branch: main", "main-only environment branch rule"),
    ("Environment localcluster exists and allows deployments from main.", "environment setup checkpoint"),
    ("## 13. First Deploy From GitHub Actions", "first CD deploy step after environment setup"),
    ("publishes the GHCR image and migration bundle only when the run is for `refs/heads/main`", "main-only CI publishing explanation"),
    ("Optional sanity check: before deploying, confirm the image tag exists.", "optional image check wording"),
    ("migration bundle artifact is missing or expired", "expired CI artifact recovery guidance"),
    ("pins PostgreSQL and Redis to exact versioned image tags", "pinned database image guidance"),
    ("If this is the only app on these four nodes, keep the default ports and continue.", "single-site default guidance"),
    ("If another LocalCluster app already runs on these nodes", "side-by-side settings warning"),
    ("### Optional: Second Fork On The Same Nodes", "second-fork side-by-side subsection"),
    ("For a second fork on the same nodes, do not reuse these values from the first app", "unique side-by-side values list"),
    ("Second-fork flow on already-prepared nodes", "second-fork execution flow"),
    ("prepare-existing-localcluster-app.sh", "existing cluster app preparation guidance"),
    ("Do not rerun bootstrap-node.sh or prepare-fresh-linux-machines.sh for already-prepared nodes", "side-by-side rerun warning"),
    ("this fork's deploy key installed on the nodes", "side-by-side validation ordering warning"),
    ("same Cloudflare account", "shared tunnel Cloudflare account limitation"),
    ("gh repo clone \"$LOCALCLUSTER_REPO\"", "fork-safe clone command"),
    ("gh repo view --json nameWithOwner,url,defaultBranchRef", "repository identity checkpoint"),
    ("Deployment identity checkpoint", "deployment identity checkpoint before setup"),
    ("git add Deployment/LocalCluster/inventory/prod/group_vars/all.yml", "deployment settings commit command"),
    ("needs committed `all.yml` settings and committed `hosts.yml` inventory", "committed settings and inventory explanation"),
    ("git status --short Deployment/LocalCluster/inventory/prod/group_vars/all.yml Deployment/LocalCluster/inventory/prod/hosts.yml Deployment/LocalCluster/inventory/prod/vault.yml", "pre-push deployment file clean-state check"),
    ("Workflow permissions: Read and write permissions", "fork GitHub Actions package write prerequisite"),
    ("`app_image`", "side-by-side app image uniqueness"),
    ("`migration_bundle_name`", "side-by-side migration bundle uniqueness"),
    ("same machine IPs", "side-by-side reused machine IP guidance"),
    ("`cloudflare_tunnel_name`, and Cloudflare tunnel token", "side-by-side shared tunnel guidance"),
    ("Add this fork's public_hostname to the existing Cloudflare tunnel", "second-fork Cloudflare hostname step"),
    ("open the existing tunnel and add the fork's `public_hostname`", "second-fork existing tunnel guidance"),
    ("secondnotes", "side-by-side example app"),
    ("LOCALCLUSTER_RUNNER_LABEL", "side-by-side runner label variable guidance"),
    ("Repository -> Settings -> Secrets and variables -> Actions -> Variables", "GitHub repository variables UI path"),
    ("No GitHub token goes into the vault.", "no stored registry token guidance"),
    ("only `read:packages`", "minimum registry permission for optional manual-deploy tokens"),
    ("Name: ANSIBLE_VAULT_PASSWORD", "manual GitHub vault secret guidance"),
    ("This secret is the Ansible Vault password.", "vault secret purpose"),
    ("release-manifest.json", "release manifest explanation"),
    ("### Runner And Docker Storage Maintenance", "maintenance workflow guidance"),
    ("### Deployment lock", "deployment lock recovery guidance"),
    ("### Tool provisioning: --check versus --provision", "check-only versus provisioning guidance"),
    ("Runner policy:", "self-hosted runner policy"),
    ("summary.sh", "deployment summary command guidance"),
    ("doctor.sh", "doctor readiness command guidance"),
    ("acceptance-check.sh", "acceptance check guidance"),
    ("report-nodes.sh", "node report guidance"),
    ("list-deployed-apps.sh", "deployed app marker listing guidance"),
    ("validate-side-by-side.sh", "side-by-side marker validation guidance"),
    ("verify-backup.sh", "backup verification guidance"),
    ("check-github-runner.sh", "GitHub runner API check guidance"),
    ("check-cloudflare-tunnel.sh", "Cloudflare read-only check guidance"),
]:
    if needle not in guide:
        fail(f"Deployment/LocalCluster/HowToDeployLocalCluster.md: missing {why}")
if "gh repo clone Grumlebob/BlazorAutoApp" in guide:
    fail("Deployment/LocalCluster/HowToDeployLocalCluster.md: clone commands must be fork-safe, not hardcoded to the original repository")

for line_number, line in enumerate(guide.splitlines(), start=1):
    if 'ansible ' in line and '-a "cd ' in line and "-m ansible.builtin.shell" not in line:
        fail(
            "Deployment/LocalCluster/HowToDeployLocalCluster.md:"
            f"{line_number}: ansible commands using cd/&& must use -m ansible.builtin.shell"
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
    if f"`{key}`" not in guide:
        fail(f"Deployment/LocalCluster/HowToDeployLocalCluster.md: missing all.yml setting documentation: {key}")

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
for needle in ['ALLOWED_EVENTS = {"push"}', "verify_publishing_job", "/attempts/{attempt}/jobs", 'job.get("run_attempt")', 'job.get("head_sha")']:
    if needle not in ci_provenance:
        fail(f"CI release provenance: missing publishing verification contract {needle}")

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
    ("rhysd/actionlint:1.7.12", "current actionlint container"),
    ("node-version: 24", "current Node.js LTS setup"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh app_image", "shared release image setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_bundle_name", "shared migration bundle setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_runtime", "shared migration runtime setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_artifact_name", "shared migration artifact setting"),
    ("dotnet restore", "restore step"),
    ("dotnet build --configuration Release --no-restore", "Release build step"),
    ("dotnet test --configuration Release --no-build", "test step"),
    ("dotnet ef migrations bundle", "migration bundle build"),
    ('--runtime "${MIGRATION_RUNTIME}"', "shared migration runtime usage"),
    ("docker build", "Docker image build"),
    ("--pull", "Docker build base image freshness"),
    ("postgres:18.4-alpine3.23", "PostgreSQL 18 integration test image pre-pull"),
    ("redis:8.8.0-alpine3.23", "Redis 8 integration test image pre-pull"),
    ("if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'", "main-only artifact/image publish guard"),
    ("name: ${{ steps.release_settings.outputs.migration_artifact_name }}", "shared migration artifact upload name"),
    ("retention-days: 7", "short migration artifact retention"),
    ("Remove this run's local Docker image", "owned CI image cleanup step"),
    ("bash Deployment/LocalCluster/Scripts/ci-docker-smoke.sh --cleanup-only", "interrupted-run smoke cleanup"),
    ("always() && steps.ci_smoke.outcome != 'skipped'", "always-run interrupted smoke cleanup guard"),
    ('docker image rm "${APP_IMAGE}:${CI_IMAGE_TAG}"', "exact-tag CI image removal"),
    ('ci_image_tag="${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"', "per-run CI image tag"),
    ("bash Scripts/CI/check-runner-capacity.sh", "report-only runner capacity check"),
    ("bash Deployment/LocalCluster/Scripts/ci-docker-smoke.sh", "Docker and browser smoke"),
    ("bash Deployment/LocalCluster/Scripts/Tests/test-ci-docker-smoke.sh", "Docker smoke resource lifecycle test"),
    ("python3 -m unittest Scripts/CI/tests/test_migration_staging_artifact.py", "migration staging provenance tests"),
    ("Deployment/Common/Scripts/Tests/test_release_contract.py", "release manifest contract tests"),
    ("Deployment/Common/Scripts/Tests/test_ci_provenance.py", "CI provenance selection tests"),
    ("Deployment/Common/Scripts/Tests/test_target_gate.py", "exact deployment target gate fixtures"),
    ("bash Deployment/LocalCluster/Scripts/Tests/test-verify-release-identity.sh", "release identity fixture test"),
    ("bash Deployment/LocalCluster/Scripts/Tests/test-localcluster-maintenance.sh", "maintenance fixture test"),
    ("bash Deployment/LocalCluster/Scripts/Tests/test-prune-docker-residue-low-disk.sh", "Docker cleanup fixture test"),
    ("bash Deployment/Common/Scripts/Tests/test-prune-actions-runner-residue.sh", "runner residue fixture test"),
    ("python3 Deployment/LocalCluster/Scripts/Tests/test_prune_ci_residue.py", "CI residue safeguard tests"),
    ("python3 Deployment/LocalCluster/Scripts/Tests/test_runner_identity.py", "runner identity fixtures"),
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
upload_pos = ci.find("Upload migration bundle")
if push_pos < 0 or upload_pos < 0 or upload_pos < push_pos:
    fail(".github/workflows/ci.yml: migration bundle upload must happen after Docker image push")
# Artifact retention and host cleanup belong to the maintenance workflow,
# which runs under the deployment lock and protects deployed releases.
maintenance = read(".github/workflows/localcluster-docker-maintenance.yml")
for needle, why in [
    ("workflow_dispatch:", "manual maintenance trigger"),
    ("# schedule:", "schedule shipped commented out for forks to enable"),
    ("localcluster-books", "app-specific self-hosted runner label fallback"),
    ("bash Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh", "locked maintenance runner"),
    ("install-ansible.sh --check", "check-only Ansible activation"),
    ("prune-migration-artifacts:", "artifact retention job"),
    ("actions: write", "permission to prune old CI artifacts"),
    ("bash Deployment/Common/Scripts/prune-actions-artifacts.sh", "shared artifact pruning script"),
    ("--keep 2", "bounded migration artifact keep count"),
    ("--protect-run-id", "deployed release artifacts are protected"),
    ("find-successful-ci-run.py --target-sha", "deployed commits mapped to their CI runs"),
]:
    if needle not in maintenance:
        fail(f".github/workflows/localcluster-docker-maintenance.yml: missing {why}")
if re.search(r"(?m)^\s+schedule:", maintenance):
    fail(".github/workflows/localcluster-docker-maintenance.yml: ship the schedule commented out; forks enable it")
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
    if "dotnet ef migrations bundle" in publisher_job:
        fail(".github/workflows/ci.yml: publish-main must not rebuild the migration bundle")
    staging_upload = workflow_step("validate", "Upload migration staging artifact")
    if (
        "-staging-${{ github.run_id }}-${{ github.run_attempt }}" not in staging_upload
        or "migration-provenance.json" not in staging_upload
        or "retention-days: 1" not in staging_upload
        or "if-no-files-found: error" not in staging_upload
    ):
        fail(".github/workflows/ci.yml: staging artifact must use a unique short-retention name and the provenance file")
    staging_validation = workflow_step("publish-main", "Validate migration staging artifact")
    if (
        "migration_staging_artifact.py validate" not in staging_validation
        or "-staging-${{ github.run_id }}-${{ github.run_attempt }}" not in publisher_job
        or publisher_job.find("Validate migration staging artifact") > publisher_job.find("Build Docker image")
        or publisher_job.find("Validate migration staging artifact") > publisher_job.find("Login to GHCR")
    ):
        fail(".github/workflows/ci.yml: publish-main must verify the exact staging input before building or publishing")
    if publisher_job.find("ci-docker-smoke.sh") < 0 or publisher_job.find("ci-docker-smoke.sh") > publisher_job.find("Push Docker image"):
        fail(".github/workflows/ci.yml: publish-main must smoke-test the image before pushing it")
    final_upload = workflow_step("publish-main", "Upload migration bundle")
    if (
        "release-manifest.json" not in final_upload
        or "migration-provenance.json" in final_upload
        or "retention-days: 7" not in final_upload
    ):
        fail(".github/workflows/ci.yml: final release artifact must be the bundle plus release-manifest.json")
    manifest_step = workflow_step("publish-main", "Resolve pushed image digest and write release manifest")
    for needle in ('"schema_version": 1', '"image_digest": digest', '"ordered_migration_ids"', '"bundle_sha256"'):
        if needle not in manifest_step:
            fail(f".github/workflows/ci.yml: release manifest step is missing {needle}")

deploy_lan = read(".github/workflows/cd-localcluster.yml")
for needle, why in [
    ("name: CD - Deploy LocalCluster", "CD workflow name"),
    ("bash Deployment/Common/Scripts/validate-common-release.sh", "common release validation step"),
    ("actions: read", "permission to inspect CI workflow runs"),
    ("environment:", "GitHub deployment environment"),
    ("LOCALCLUSTER_ENVIRONMENT", "optional side-by-side GitHub environment variable"),
    ("concurrency:", "deployment concurrency guard"),
    ("group: cd-localcluster", "CD concurrency group"),
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
    ("find-successful-ci-run.py --target-sha \"$TARGET_SHA\" --json", "successful CI gate for the target commit"),
    ("CI_RUN_ID=", "CI run id export"),
    ("CI_RUN_ATTEMPT=", "CI run attempt export"),
    ("validate_release_manifest.py", "release manifest validation"),
    ('--expected-ci-run-attempt "$CI_RUN_ATTEMPT"', "release manifest bound to the CI attempt"),
    ("release_image_digest=${RELEASE_IMAGE_DIGEST}", "digest-pinned deployment"),
    ('-e @"${GHCR_EXTRA_VARS_FILE}"', "workflow-token registry credentials"),
    ("GHCR_TOKEN: ${{ secrets.GITHUB_TOKEN }}", "workflow token instead of a stored PAT"),
    ('rm -f "${GHCR_EXTRA_VARS_FILE}"', "registry credential file cleanup"),
    ("verify-release-identity.sh", "running release identity verification"),
    ("timeout-minutes: 60", "bounded deploy job"),
    ("uses: actions/download-artifact@v8", "CI migration artifact download"),
    ("name: ${{ env.MIGRATION_ARTIFACT_NAME }}", "shared migration artifact download name"),
    ("run-id: ${{ env.CI_RUN_ID }}", "download artifact from matching CI run"),
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
download_step = re.search(r"(?ms)^      - name: Download release artifact from CI\n.*?(?=^      - name: |\Z)", deploy_lan)
if download_step is None or "if:" in download_step.group(0):
    fail(".github/workflows/cd-localcluster.yml: download the release artifact for every deploy; the manifest is always needed")
if "vault_ghcr_token" in read("Deployment/LocalCluster/inventory/prod/vault.example.yml").replace("# vault_ghcr_token", ""):
    fail("Deployment/LocalCluster/inventory/prod/vault.example.yml: GHCR credentials must stay optional")
app_tasks = read("Deployment/LocalCluster/ansible/roles/app/tasks/main.yml")
for needle, why in [
    ("Pull application image with command-owned registry credentials", "single command-owned registry login and pull"),
    ('export DOCKER_CONFIG="$docker_config"', "temporary registry credential store"),
    ("docker compose up -d --pull always --remove-orphans", "pull and start the exact image"),
    ("no_log: true", "registry credentials kept out of logs"),
]:
    if needle not in app_tasks:
        fail(f"Deployment/LocalCluster/ansible/roles/app/tasks/main.yml: missing {why}")
if "- name: Log in to GHCR" in app_tasks:
    fail("Deployment/LocalCluster/ansible/roles/app/tasks/main.yml: do not leave a persistent GHCR login on app nodes")
for path in ("Deployment/LocalCluster/HowToDeployLocalCluster.md", "docs/HowToForkThisRepo.md"):
    release_guide = read(path)
    for needle in ("Append the same scanned key only after the fingerprints match",
                   'cat "$host_key_candidate" >> ~/.ssh/known_hosts',
                   "successful `publish-main` job on the same run attempt"):
        if needle not in release_guide:
            fail(f"{path}: document verified SSH host keys and exact-attempt publishing provenance")
if "Tokens (classic)" in guide or "vault_ghcr_token: <github-token" in guide:
    fail("Deployment/LocalCluster/HowToDeployLocalCluster.md: CD no longer needs a stored GHCR token; do not instruct users to create one")
if "image_tag" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: manual image_tag input should not be required")
if "Deploy Ship To LAN" in deploy_lan or "Deploy App To LAN" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: workflow name must be explicitly CD-oriented")
if "dotnet ef migrations bundle" in deploy_lan or "dotnet restore" in deploy_lan or "dotnet tool restore" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: CD must consume CI artifacts instead of rebuilding them")

find_ci = read("Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py")
for needle, why in [
    ("GITHUB_REPOSITORY", "repository input"),
    ("GITHUB_SHA", "commit input"),
    ("GITHUB_TOKEN", "GitHub token input"),
    ("actions/workflows", "workflow runs API"),
    ('selected["conclusion"] != "success"', "successful CI conclusion requirement"),
    ('ALLOWED_EVENTS = {"push"}', "pull request run exclusion"),
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
    ("set -euo pipefail", "strict migration shell"),
    ("Write LocalCluster app ownership markers", "app ownership marker phase"),
    ("app_marker", "app ownership marker role"),
]:
    if needle not in site:
        fail(f"Deployment/LocalCluster/ansible/playbooks/site.yml: missing {why}")
stage_pos = site.find("Stage the exact app image before any app interruption")
stop_pos = site.find("- name: Stop app containers before migration")
apps_pos = site.find("- name: Deploy app servers")
caddy_pos = site.find("- name: Deploy Caddy and Cloudflare Tunnel")
if stage_pos < 0 or stop_pos < 0 or stage_pos > stop_pos:
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: stage the exact app image before stopping apps")
if "Require the registry digest on the staged image" not in site:
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: staged image must be checked against the release digest")
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
        ("docker compose up -d --pull always", "pull and start requested image"),
        ("http://127.0.0.1:{{ app_port }}/health/ready", "local readiness wait"),
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
        ("acceptance check ok", "clear success line"),
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

verify_deployment = read("Deployment/LocalCluster/Scripts/verify-deployment.sh")
for needle, why in [
    ("acceptance-check.sh", "acceptance check wrapper"),
    ("deployment verification ok", "clear success line"),
]:
    if needle not in verify_deployment:
        fail(f"Deployment/LocalCluster/Scripts/verify-deployment.sh: missing {why}")
if "http://localhost" in verify_deployment:
    fail("Deployment/LocalCluster/Scripts/verify-deployment.sh: use 127.0.0.1 instead of localhost for local health checks")

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

for workflow in workflow_paths:
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
require_contains(
    ".github/workflows/auto-merge-dependabot.yml",
    "Verify GitHub CLI",
    "self-hosted auto-merge gh availability check",
)
# Dependabot auto-merge must merge only the exact commit CI tested, keep major
# bumps and deployment/workflow logic changes for a human, and keep the
# branches Dependabot tracks.
auto_merge = read(".github/workflows/auto-merge-dependabot.yml")
for needle, why in [
    ("startsWith(github.event.workflow_run.head_branch, 'dependabot/')", "Dependabot branch scope"),
    ('"$source_workflow_path" != \'.github/workflows/ci.yml\'', "CI workflow identity check"),
    ('"$head_sha" != "$SOURCE_SHA"', "exact tested head check"),
    ("semver-major", "major update manual review"),
    ("deployment-surface", "deployment surface manual review"),
    ("workflow-change-not-limited-to-action-version-updates", "workflow logic manual review"),
    ("gh pr merge \"$pr\" --disable-auto", "auto-merge disabled when manual review is required"),
    ("expected_head_sha=\"$SOURCE_SHA\"", "branch refresh pinned to the tested head"),
    ("secrets.GH_TOKEN || secrets.GITHUB_TOKEN", "optional workflow-capable token"),
    ("Auto-merge deferred", "visible deferral reason"),
    ("gh pr merge \"$pr\" --merge --auto", "queued merge after required checks"),
]:
    if needle not in auto_merge:
        fail(f".github/workflows/auto-merge-dependabot.yml: missing {why}")
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
for path in ("compose/docker-compose.yml", "AgentSetup.md", "Scripts/bootstrap-node.sh", "Scripts/setup-status.sh", "Scripts/setup-next-step.sh", "Scripts/doctor.sh", "Scripts/run-maintenance.sh", "ansible/playbooks/PrepareSingleNode.yml", "ansible/playbooks/site.yml"):
    require_file(single + "/" + path)
single_compose = read(single + "/compose/docker-compose.yml")
for binding in re.findall(r'(?m)^      - "([^"\n]+:[0-9${}A-Z_]+)"$', single_compose):
    if not binding.startswith("127.0.0.1:"):
        fail("localsinglenode: published ports must bind loopback")
if single_compose.count('"127.0.0.1:') != 3:
    fail("localsinglenode: all three service publications must bind loopback")
require_contains(single + "/compose/docker-compose.yml", 'LocalAccounts__Enabled: "false"', "deployment account seeding disabled")
for needle in ("find-successful-ci-run.py --target-sha", "validate_release_manifest.py", "release_image_digest", "with-deploy-lock.sh", "git merge-base --is-ancestor", "--expected-ci-run-attempt", "LOCALSINGLENODE_HOST", "TARGET: localsinglenode"):
    require_contains(".github/workflows/cd-localsinglenode.yml", needle, "strict single-node release contract")
for path in (".github/workflows/cd-localsinglenode.yml", ".github/workflows/localsinglenode-maintenance.yml"):
    workflow = read(path)
    if "vars.LOCALSINGLENODE_HOST" not in workflow or "test -n" not in workflow or "'localsinglenode-books'" not in workflow:
        fail("localsinglenode: workflow needs explicit host and app runner label")
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
require_contains("Deployment/LocalCluster/Scripts/ci-docker-smoke.sh", "Scripts/Test-DeployedSite.ps1", "HTTP form acceptance in CI")
require_contains(single + "/Scripts/lib/platform_check.py", '"WSL_DISTRO_NAME"', "native deployment boundary")
require_contains(single + "/Scripts/lib/doctor.py", '"ip", "-j", "-4", "address", "show"', "mDNS check discovers the interface owning the deployment IPv4")
require_contains(single + "/Scripts/lib/doctor.py", '"ResolveHostName", "iisiu", str(index), "0", name, "0", "0"', "mDNS check resolves the deployment name on its LAN interface")
require_contains(single + "/Scripts/lib/doctor.py", 'data[4] == machine["ip"]', "mDNS check requires the exact deployment IPv4")
require_contains(single + "/Scripts/lib/doctor.py", '"--property=Id,ActiveState,User,WorkingDirectory"', "read-only runner service inspection without deploy home access")
require_contains(single + "/Scripts/lib/collisions.py", 'recorded_source.casefold() == source.casefold()', "case-insensitive GitHub repository ownership with exact app roots")
require_contains(single + "/Scripts/lib/collisions.py", '(network.get("IPAM") or {}).get("Config") or []', "nullable built-in Docker network IPAM while checking foreign subnets")
require_contains(single + "/Scripts/acceptance-check.sh", 'lib/readiness.py', "bounded LAN warmup before the unchanged full acceptance check")
require_contains(single + "/Scripts/lib/readiness.py", 'timeout=180', "180-second LAN readiness deadline")
require_contains(single + "/Scripts/run-maintenance.sh", '--report-fresh-since "$requested"', "requested backups prove fresh completion before maintenance")
require_contains(single + "/Scripts/lib/backup.py", 'completed < started', "requested backups cannot reuse stale completion markers")
require_contains(single + "/Scripts/lib/backup.py", 'Fresh protected backup:', "explicit fresh dump evidence without secret contents")
require_contains(single + "/Scripts/acceptance-check.sh", 'public-acceptance-check.sh', "public acceptance after LAN acceptance")
require_contains(single + "/Scripts/lib/readiness.py", 'response.read(64).strip() == b"Healthy"', "readiness rejects empty HTTP 200")
require_contains(single + "/Scripts/public-acceptance-check.sh", '-BaseUrl "$PUBLIC_URL"', "configured public HTTPS acceptance")
require_contains(single + "/Scripts/lib/public_config.py", 'os.O_EXCL | os.O_NOFOLLOW', "protected public secret output")
require_contains(single + "/Scripts/lib/public_config.py", 'claims.get("t") != tunnel_id', "matching connector credential identity")
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
require_contains(".github/workflows/cd-localsinglenode.yml", '-e @"$PUBLIC_EXTRA_VARS_FILE"', "validated public inputs deployed")
require_contains(".github/workflows/cd-localsinglenode.yml", 'rm -f -- "$PUBLIC_EXTRA_VARS_FILE"', "temporary connector credential cleanup")
require_contains("Deployment/Common/Scripts/Component/lib/cloudflare_tunnel.py", 'Tunnel name exists without recorded ownership', "foreign tunnel refusal")
require_contains("Deployment/Common/Scripts/Component/lib/cloudflare_tunnel.py", 'replacement is refused', "foreign DNS refusal")


if failures:
    print("Deployment audit failed:")
    for failure in failures:
        print(f" - {failure}")
    sys.exit(1)

print("Deployment audit passed.")
