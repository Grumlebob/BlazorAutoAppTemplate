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
    "Deployment/Common/Scripts/read-release-setting.sh",
    "Deployment/Common/Scripts/validate-common-release.sh",
    "Deployment/Common/Scripts/Component/lib/read-release-setting.py",
    "Deployment/Common/Scripts/Component/lib/release_settings.py",
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
    "Deployment/LocalCluster/ansible/roles/app_marker/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/app_marker/templates/app-marker.env.j2",
    "Deployment/LocalCluster/ansible/roles/caddy/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/caddy/templates/app.caddy.j2",
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/docker/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/firewall/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2",
    "Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.service.j2",
    "Deployment/LocalCluster/ansible/roles/mint_base/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/postgres/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/postgres/templates/node-db.env.j2",
    "Deployment/LocalCluster/ansible/roles/redis/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/ssh_hardening/tasks/main.yml",
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
    "Deployment/LocalCluster/Scripts/audit-deployment.sh",
    "Deployment/LocalCluster/Scripts/find-successful-ci-run.sh",
    "Deployment/LocalCluster/Scripts/generate-inventory.sh",
    "Deployment/LocalCluster/Scripts/install-github-runner.sh",
    "Deployment/LocalCluster/Scripts/install-ansible.sh",
    "Deployment/LocalCluster/Scripts/read-deploy-setting.sh",
    "Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py",
    "Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py",
    "Deployment/LocalCluster/Scripts/Component/lib/find-successful-ci-run.py",
    "Deployment/LocalCluster/Scripts/Component/lib/generate-inventory.py",
    "Deployment/LocalCluster/Scripts/Component/lib/read-deploy-setting.py",
    "Deployment/LocalCluster/Scripts/Component/lib/validate-deploy-settings.py",
    "Deployment/LocalCluster/Scripts/Component/lib/validate-vault.py",
    "Deployment/LocalCluster/Scripts/Component/node-db/backup-db.sh",
    "Deployment/LocalCluster/Scripts/Component/node-db/restore-db.sh",
    "Deployment/LocalCluster/Scripts/preflight.sh",
    "Deployment/LocalCluster/Scripts/prepare-existing-localcluster-app.sh",
    "Deployment/LocalCluster/Scripts/prepare-fresh-linux-machines.sh",
    "Deployment/LocalCluster/Scripts/list-deployed-apps.sh",
    "Deployment/LocalCluster/Scripts/report-nodes.sh",
    "Deployment/LocalCluster/Scripts/setup-cloudflare-tunnel.sh",
    "Deployment/LocalCluster/Scripts/setup-control-machine.sh",
    "Deployment/LocalCluster/Scripts/setup-secrets.sh",
    "Deployment/LocalCluster/Scripts/Component/install-ansible.sh",
    "Deployment/LocalCluster/Scripts/Component/ping-fresh-machines.sh",
    "Deployment/LocalCluster/Scripts/Component/with-deploy-lock.sh",
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
    "Deployment/LocalCluster/Scripts/with-deploy-lock.sh",
    "BlazorAutoApp/Program.cs",
    "BlazorAutoApp/BlazorAutoApp.csproj",
]
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
    ("Tokens (classic)", "GHCR classic token UI guidance"),
    ("Select only `read:packages`", "minimum GHCR token permission guidance"),
    ("GitHub only shows it once", "GitHub token one-time visibility warning"),
    ("Name: ANSIBLE_VAULT_PASSWORD", "manual GitHub vault secret guidance"),
    ("This secret is the Ansible Vault password, not the GHCR token.", "vault secret distinction"),
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
        ("improveddb", "ship"),
        ("/opt/improveddb", "/opt/ship"),
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
for key in all_var_keys:
    if f"`{key}`" not in guide:
        fail(f"Deployment/LocalCluster/HowToDeployLocalCluster.md: missing all.yml setting documentation: {key}")

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
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_version != \"latest\"",
    "cloudflared pinned-version guard",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared --version",
    "cloudflared installed-version verification",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "path: /etc/cloudflared",
    "cloudflared config directory creation",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "This deployment supports only x86_64/amd64 Linux machines.",
    "amd64-only cloudflared guard",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared-linux-amd64.deb",
    "amd64 cloudflared package",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "tunnel-token.sha256",
    "Cloudflare tunnel token change marker",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_tunnel_token_marker_missing",
    "Cloudflare missing marker recovery",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "Compute Cloudflare tunnel token hash",
    "Cloudflare token hash computed before dependent facts",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_tunnel_token_hash_mismatch",
    "Cloudflare token mismatch detection",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_tunnel_token_changed | bool",
    "Cloudflare token change condition coerced to bool",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared service uninstall",
    "Cloudflare tunnel token rotation handling",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_allow_token_rotation",
    "side-by-side-safe Cloudflare tunnel token replacement guard",
)
require_not_contains(
    "Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_deb_arch",
    "cloudflared multi-architecture package mapping",
)
cloudflared_tasks = read("Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml")
cloudflared_refuse_match = re.search(
    r"- name: Refuse accidental Cloudflare tunnel token replacement[\s\S]+?(?=\n- name:)",
    cloudflared_tasks,
)
if cloudflared_refuse_match and "cloudflared_tunnel_token_changed" in cloudflared_refuse_match.group(0):
    fail("Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml: missing marker must recover, only hash mismatch should refuse token replacement")


ansible_cfg = read("Deployment/LocalCluster/ansible/ansible.cfg")
for needle, why in [
    ("inventory = ../inventory/prod/hosts.yml", "default production inventory"),
    ("roles_path = roles", "local roles path"),
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


deploy_app_compose = read("Deployment/LocalCluster/compose/app-server/docker-compose.yml")
for needle, why in [
    ("${APP_IMAGE}:${APP_VERSION}", "immutable image variables"),
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
    "Deployment/LocalCluster/Scripts/Component/install-ansible.sh",
    "sshpass",
    "sshpass for Ansible password bootstrap",
)
require_contains(
    "Deployment/LocalCluster/Scripts/Component/install-ansible.sh",
    "already installed",
    "idempotent Ansible install skip",
)
require_contains(
    "Deployment/LocalCluster/Scripts/setup-control-machine.sh",
    "validate-deploy-settings.sh",
    "deployment settings validation before control setup",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/caddy/tasks/main.yml",
    "creates: /usr/share/keyrings/caddy-stable-archive-keyring.gpg",
    "idempotent Caddy key installation",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/caddy/tasks/main.yml",
    "set -euo pipefail",
    "strict Caddy key installation shell",
)
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
    ("find Deployment/LocalCluster/Scripts Deployment/Common/Scripts -type f -name '*.sh'", "LocalCluster and Common shell lint roots"),
    ("bash Deployment/Common/Scripts/validate-common-release.sh", "common release validation step"),
    ("bash Deployment/LocalCluster/Scripts/audit-deployment.sh", "deployment audit step"),
    ("bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh", "rendered deployment template validation step"),
    ("python -m pip install --upgrade yamllint", "deployment lint tool install"),
    ("yamllint .github Deployment/LocalCluster Deployment/Common", "deployment YAML lint step"),
    ("rhysd/actionlint:1.7.12", "current actionlint container"),
    ("node-version: 24", "current Node.js LTS setup"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh app_image", "shared release image setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_bundle_name", "shared migration bundle setting"),
    ("bash Deployment/Common/Scripts/read-release-setting.sh migration_artifact_name", "shared migration artifact setting"),
    ("dotnet restore", "restore step"),
    ("dotnet build --configuration Release --no-restore", "Release build step"),
    ("dotnet test --configuration Release --no-build", "test step"),
    ("dotnet ef migrations bundle", "migration bundle build"),
    ("docker build", "Docker image build"),
    ("--pull", "Docker build base image freshness"),
    ("postgres:18.4-alpine3.23", "PostgreSQL 18 integration test image pre-pull"),
    ("redis:8.8.0-alpine3.23", "Redis 8 integration test image pre-pull"),
    ("if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'", "main-only artifact/image publish guard"),
    ("name: ${{ env.MIGRATION_ARTIFACT_NAME }}", "shared migration artifact upload name"),
    ("docker push \"${APP_IMAGE}:${{ github.sha }}\"", "immutable configured image push"),
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
if "${APP_IMAGE}:latest" in ci or "docker push \"${APP_IMAGE}:latest\"" in ci:
    fail(".github/workflows/ci.yml: CI must publish only immutable Git SHA image tags")
if "secrets.ANSIBLE_VAULT_PASSWORD" in ci:
    fail(".github/workflows/ci.yml: CI must not require the production Ansible Vault password")
if "ansible-lint" in ci or "ansible-vault encrypt" in ci:
    fail(".github/workflows/ci.yml: CI must not run dummy-vault Ansible linting")

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
    ("echo \"APP_VERSION=${GITHUB_SHA}\"", "automatic selected-ref image tag"),
    ("bash Deployment/LocalCluster/Scripts/find-successful-ci-run.sh", "successful CI gate"),
    ("CI_RUN_ID=", "CI run id export"),
    ("docker manifest inspect \"${APP_IMAGE}:${APP_VERSION}\"", "image existence check"),
    ("uses: actions/download-artifact@v8", "CI migration artifact download"),
    ("name: ${{ env.MIGRATION_ARTIFACT_NAME }}", "shared migration artifact download name"),
    ("run-id: ${{ env.CI_RUN_ID }}", "download artifact from matching CI run"),
    ("chmod 0750 \"artifacts/migrations/${MIGRATION_BUNDLE_NAME}\"", "restore migration bundle execute bit"),
    ("bash Deployment/LocalCluster/Scripts/preflight.sh deploy", "deploy preflight"),
    ("with-deploy-lock.sh", "cross-repo deployment lock"),
    ("app_version=${APP_VERSION}", "selected-ref image deployment"),
    ("app_image=${APP_IMAGE}", "shared image extra var"),
    ("migration_bundle_name=${MIGRATION_BUNDLE_NAME}", "shared migration bundle extra var"),
    ("source_repo_url=${SOURCE_REPO_URL}", "source repository marker metadata"),
    ("${{ github.workspace }}/artifacts/migrations/${MIGRATION_BUNDLE_NAME}", "absolute migration bundle path"),
    ("bash Deployment/LocalCluster/Scripts/acceptance-check.sh", "full acceptance verification"),
    ("mktemp \"${RUNNER_TEMP:-/tmp}/${APP_NAME}_ansible_vault_password.XXXXXX\"", "private vault password temp file"),
    ("rm -f \"${ANSIBLE_VAULT_PASSWORD_FILE}\"", "vault password file cleanup"),
]:
    if needle not in deploy_lan:
        fail(f".github/workflows/cd-localcluster.yml: missing {why}")
if "image_tag" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: manual image_tag input should not be required")
if "Deploy Ship To LAN" in deploy_lan or "Deploy App To LAN" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: workflow name must be explicitly CD-oriented")
if "dotnet ef migrations bundle" in deploy_lan or "dotnet restore" in deploy_lan or "dotnet tool restore" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: CD must consume CI artifacts instead of rebuilding them")

find_ci = read("Deployment/LocalCluster/Scripts/Component/lib/find-successful-ci-run.py")
for needle, why in [
    ("GITHUB_REPOSITORY", "repository input"),
    ("GITHUB_SHA", "commit input"),
    ("GITHUB_TOKEN", "GitHub token input"),
    ("actions/workflows", "workflow runs API"),
    ("conclusion\") == \"success\"", "successful CI conclusion requirement"),
    ("event\") != \"pull_request\"", "pull request run exclusion"),
]:
    if needle not in find_ci:
        fail(f"Deployment/LocalCluster/Scripts/Component/lib/find-successful-ci-run.py: missing {why}")


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
if re.search(r"name: Stop existing app stack[\s\S]+?failed_when: false", site):
    fail("Deployment/LocalCluster/ansible/playbooks/site.yml: Stop existing app stack must not suppress all failures")

for path, checks in {
    "Deployment/LocalCluster/ansible/roles/mint_base/tasks/main.yml": [
        ("name: deploy", "deploy user creation"),
        ("python3-debian", "deb822 repository module dependency"),
        ("NOPASSWD:ALL", "passwordless sudo for automation"),
        ("90-localcluster-deploy", "neutral LocalCluster sudoers file"),
        ("authorized_keys", "deploy SSH public key installation"),
        ("deploy_private_key_file", "control-node private key installation"),
        ("inventory_hostname in groups[\"load_balancer\"]", "private key limited to control node"),
        ("known_hosts", "control-node SSH host key setup"),
        ("ssh-keyscan", "deployment node host key scan"),
        ("path: \"{{ deploy_root }}\"", "deployment root creation"),
    ],
    "Deployment/LocalCluster/ansible/roles/docker/tasks/main.yml": [
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
        ("POSTGRES_PORT={{ postgres_port }}", "PostgreSQL port env rendering"),
        ("REDIS_PORT={{ redis_port }}", "Redis port env rendering"),
    ],
    "Deployment/LocalCluster/ansible/roles/postgres/templates/node-db.env.j2": [
        ("COMPOSE_PROJECT_NAME={{ app_name }}", "explicit Compose project name"),
        ("APP_NAME={{ app_name }}", "node-db app identity env marker"),
        ("POSTGRES_PORT={{ postgres_port }}", "PostgreSQL port env rendering"),
        ("REDIS_PORT={{ redis_port }}", "Redis port env rendering"),
    ],
    "Deployment/LocalCluster/ansible/roles/app_marker/tasks/main.yml": [
        ("/etc/localcluster/apps", "app marker directory"),
        ("app-marker.env.j2", "app marker template"),
        ("{{ app_name }}.env", "per-app marker file"),
    ],
    "Deployment/LocalCluster/ansible/roles/app_marker/templates/app-marker.env.j2": [
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
if "90-{{ app_name }}-deploy" in read("Deployment/LocalCluster/ansible/roles/mint_base/tasks/main.yml"):
    fail("Deployment/LocalCluster/ansible/roles/mint_base/tasks/main.yml: sudoers file must be cluster-neutral, not app-named")
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

deploy_lock = read("Deployment/LocalCluster/Scripts/Component/with-deploy-lock.sh")
for needle, why in [
    ("mkdir \"$LOCK_DIR\"", "directory-based cross-repo deployment lock"),
    ("LOCALCLUSTER_DEPLOY_LOCK_DIR", "configurable lock directory"),
    ("LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS", "configurable lock timeout"),
    ("LOCALCLUSTER_DEPLOY_LOCK_STALE_SECONDS", "stale lock cleanup"),
    ("created_epoch", "stale lock age marker"),
]:
    if needle not in deploy_lock:
        fail(f"Deployment/LocalCluster/Scripts/Component/with-deploy-lock.sh: missing {why}")

node_main_deploy_lock = read("Deployment/LocalCluster/Scripts/Component/with-node-main-deploy-lock.sh")
for needle, why in [
    ("ansible-inventory", "node-main lookup from inventory"),
    ("node-main", "node-main remote lock target"),
    ("ssh", "remote lock transport"),
    ("try_acquire_lock", "remote lock acquisition"),
    ("LOCALCLUSTER_DEPLOY_LOCK_DIR", "shared lock directory"),
    ("LOCK_STALE_SECONDS", "stale lock cleanup"),
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
    ("gh release view --repo actions/runner", "runner release lookup"),
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
    ("RUNNER_NEEDS_RECONFIGURE", "incomplete runner reconfiguration state"),
    ("Cleaning incomplete GitHub Actions runner directory", "incomplete runner cleanup"),
    ("/opt/actions-runner-${APP_NAME}", "app-specific runner directory"),
    ("sudo ./svc.sh install deploy", "runner service install as deploy"),
]:
    if needle not in runner_setup:
        fail(f"Deployment/LocalCluster/Scripts/install-github-runner.sh: missing {why}")
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


if failures:
    print("Deployment audit failed:")
    for failure in failures:
        print(f" - {failure}")
    sys.exit(1)

print("Deployment audit passed.")
