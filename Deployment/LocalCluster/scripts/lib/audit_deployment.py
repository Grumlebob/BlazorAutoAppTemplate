#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
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
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


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
    "Deployment/LocalCluster/HowToDeployLocalCluster.md",
    ".github/workflows/ci.yml",
    ".github/workflows/cd-localcluster.yml",
    ".ansible-lint.yml",
    ".yamllint.yml",
    ".config/dotnet-tools.json",
    ".gitignore",
    "Deployment/LocalCluster/machines.example.yml",
    "Deployment/LocalCluster/inventory/prod/hosts.yml",
    "Deployment/LocalCluster/inventory/prod/group_vars/all.yml",
    "Deployment/LocalCluster/inventory/prod/vault.example.yml",
    "Deployment/LocalCluster/ansible/ansible.cfg",
    "Deployment/LocalCluster/ansible/playbooks/PrepareFreshLinuxMachine.yml",
    "Deployment/LocalCluster/ansible/playbooks/site.yml",
    "Deployment/LocalCluster/ansible/roles/app/tasks/main.yml",
    "Deployment/LocalCluster/ansible/roles/app/templates/app.env.j2",
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
    "Deployment/LocalCluster/scripts/README.md",
    "Deployment/LocalCluster/scripts/bootstrap-node.sh",
    "Deployment/LocalCluster/scripts/check-port-collisions.sh",
    "Deployment/LocalCluster/scripts/check-vault.sh",
    "Deployment/LocalCluster/scripts/deploy.sh",
    "Deployment/LocalCluster/scripts/discover-machines.sh",
    "Deployment/LocalCluster/scripts/generate-inventory.sh",
    "Deployment/LocalCluster/scripts/install-github-runner.sh",
    "Deployment/LocalCluster/scripts/lib/audit_deployment.py",
    "Deployment/LocalCluster/scripts/lib/deploy_settings.py",
    "Deployment/LocalCluster/scripts/lib/find-successful-ci-run.py",
    "Deployment/LocalCluster/scripts/lib/generate-inventory.py",
    "Deployment/LocalCluster/scripts/lib/read-deploy-setting.py",
    "Deployment/LocalCluster/scripts/lib/validate-deploy-settings.py",
    "Deployment/LocalCluster/scripts/lib/validate-vault.py",
    "Deployment/LocalCluster/scripts/node-db/backup-db.sh",
    "Deployment/LocalCluster/scripts/node-db/restore-db.sh",
    "Deployment/LocalCluster/scripts/preflight.sh",
    "Deployment/LocalCluster/scripts/prepare-fresh-linux-machines.sh",
    "Deployment/LocalCluster/scripts/setup-cloudflare-tunnel.sh",
    "Deployment/LocalCluster/scripts/setup-control-machine.sh",
    "Deployment/LocalCluster/scripts/setup-secrets.sh",
    "Deployment/LocalCluster/scripts/support/install-ansible.sh",
    "Deployment/LocalCluster/scripts/support/ping-fresh-machines.sh",
    "Deployment/LocalCluster/scripts/support/with-deploy-lock.sh",
    "Deployment/LocalCluster/scripts/support/with-node-main-deploy-lock.sh",
    "Deployment/LocalCluster/scripts/status.sh",
    "Deployment/LocalCluster/scripts/verify-bootstrap.sh",
    "Deployment/LocalCluster/scripts/verify-deployment.sh",
    "BlazorAutoApp/Program.cs",
    "BlazorAutoApp/BlazorAutoApp.csproj",
]
for file in required_files:
    require_file(file)


removed_files = [
    "HowToDeploy.md",
    "DeploymentRefactor.md",
    ".github/workflows/deploy-lan.yml",
    "Deployment/LocalCluster/.deploy.local.env.example",
    "Deployment/LocalCluster/scripts/audit_deployment.py",
    "Deployment/LocalCluster/scripts/backup-db.sh",
    "Deployment/LocalCluster/scripts/deploy_settings.py",
    "Deployment/LocalCluster/scripts/discover-node.sh",
    "Deployment/LocalCluster/scripts/generate-inventory.py",
    "Deployment/LocalCluster/scripts/health-check.sh",
    "Deployment/LocalCluster/scripts/install-ansible.sh",
    "Deployment/LocalCluster/scripts/ping-fresh-machines.sh",
    "Deployment/LocalCluster/scripts/read-deploy-setting.py",
    "Deployment/LocalCluster/scripts/restore-db.sh",
    "Deployment/LocalCluster/scripts/validate-deploy-settings.py",
    "Deployment/LocalCluster/scripts/validate-vault.py",
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
    set(re.findall(r"(?:\./)?Deployment/LocalCluster/scripts/([A-Za-z0-9_.-]+\.sh)", guide))
    | set(re.findall(r"`([A-Za-z0-9_.-]+\.sh)`", guide))
):
    if not exists(f"Deployment/LocalCluster/scripts/{script_name}"):
        fail(
            "Deployment/LocalCluster/HowToDeployLocalCluster.md: "
            f"references missing script: Deployment/LocalCluster/scripts/{script_name}"
        )

for needle, why in [
    ("## 11. Configure The GitHub CD Environment", "dedicated GitHub environment setup step"),
    ("New environment -> localcluster", "localcluster environment creation"),
    ("Deployment branches and tags: Selected branches and tags", "deployment branch restriction instructions"),
    ("Allowed branch: main", "main-only environment branch rule"),
    ("Environment localcluster exists and allows deployments from main.", "environment setup checkpoint"),
    ("## 12. First Deploy From GitHub Actions", "first CD deploy step after environment setup"),
    ("publishes the GHCR image and migration bundle only when the run is for `refs/heads/main`", "main-only CI publishing explanation"),
    ("Optional sanity check: before deploying, confirm the image tag exists.", "optional image check wording"),
    ("migration bundle artifact is missing or expired", "expired CI artifact recovery guidance"),
    ("pins PostgreSQL and Redis to exact versioned image tags", "pinned database image guidance"),
    ("If this is the only app on these four nodes, keep the default ports and continue.", "single-site default guidance"),
    ("If another LocalCluster app already runs on these nodes", "side-by-side settings warning"),
]:
    if needle not in guide:
        fail(f"Deployment/LocalCluster/HowToDeployLocalCluster.md: missing {why}")


tracked = tracked_files()
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


for path in deployment_text_files():
    rel = path.relative_to(ROOT).as_posix()
    if rel == "Deployment/LocalCluster/scripts/lib/audit_deployment.py":
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
        fail(f"{rel}: use Deployment/LocalCluster/scripts/support/install-ansible.sh instead of distro Ansible")
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
        [sys.executable, str(ROOT / "Deployment/LocalCluster/scripts/lib/validate-deploy-settings.py")],
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
]:
    if needle not in hosts:
        fail(f"Deployment/LocalCluster/inventory/prod/hosts.yml: missing {why}")
generate_inventory = read("Deployment/LocalCluster/scripts/lib/generate-inventory.py")
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
]:
    if needle not in generate_inventory:
        fail(f"Deployment/LocalCluster/scripts/lib/generate-inventory.py: missing {why}")
if "def read_simple_group_var" in generate_inventory:
    fail("Deployment/LocalCluster/scripts/lib/generate-inventory.py: use deploy_settings.py instead of a local all.yml parser")

for path, checks in {
    "Deployment/LocalCluster/scripts/lib/read-deploy-setting.py": [
        ("load_settings", "shared deployment settings reader"),
        ("load_settings(settings_path, validate_file=True)", "settings validation before read"),
    ],
    "Deployment/LocalCluster/scripts/lib/validate-deploy-settings.py": [
        ("load_settings", "shared deployment settings validator"),
    ],
    "Deployment/LocalCluster/scripts/lib/deploy_settings.py": [
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
    ('ASPNETCORE_URLS: "http://+:${APP_PORT}"', "configured app listen port"),
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
for moving_image in ["postgres:16-alpine", "redis:7-alpine", "postgres:latest", "redis:latest"]:
    if moving_image in node_db_compose:
        fail(f"Deployment/LocalCluster/compose/node-db/docker-compose.yml: use exact image tags, not {moving_image}")


program = read("BlazorAutoApp/Program.cs")
for needle, why in [
    ("PersistKeysToStackExchangeRedis", "Redis-backed Data Protection"),
    ("UseForwardedHeaders", "forwarded header middleware"),
    ("MapHealthChecks(\"/health/live\"", "liveness health endpoint"),
    ("MapHealthChecks(\"/health/ready\"", "readiness health endpoint"),
    ("Database:RunMigrationsAtStartup", "migration startup guard"),
]:
    if needle not in program:
        fail(f"BlazorAutoApp/Program.cs: missing {why}")
require_contains(
    "BlazorAutoApp/BlazorAutoApp.csproj",
    "Microsoft.AspNetCore.DataProtection.StackExchangeRedis",
    "Redis Data Protection package",
)

require_contains(
    "Deployment/LocalCluster/scripts/support/install-ansible.sh",
    "sshpass",
    "sshpass for Ansible password bootstrap",
)
require_contains(
    "Deployment/LocalCluster/scripts/support/install-ansible.sh",
    "already installed",
    "idempotent Ansible install skip",
)
require_contains(
    "Deployment/LocalCluster/scripts/setup-control-machine.sh",
    "validate-deploy-settings.py",
    "deployment settings validation before control setup",
)
require_contains(
    "Deployment/LocalCluster/ansible/roles/caddy/tasks/main.yml",
    "creates: /usr/share/keyrings/caddy-stable-archive-keyring.gpg",
    "idempotent Caddy key installation",
)

for needle, why in [
    ("could not detect this node's LAN IP address", "clear LAN IP detection failure"),
    ("could not detect the MAC address", "clear LAN MAC detection failure"),
]:
    if needle not in read("Deployment/LocalCluster/scripts/bootstrap-node.sh"):
        fail(f"Deployment/LocalCluster/scripts/bootstrap-node.sh: missing {why}")
    if needle not in read("Deployment/LocalCluster/scripts/discover-machines.sh"):
        fail(f"Deployment/LocalCluster/scripts/discover-machines.sh: missing {why}")


ci = read(".github/workflows/ci.yml")
for needle, why in [
    ("python Deployment/LocalCluster/scripts/lib/audit_deployment.py", "deployment audit step"),
    ("python -m pip install --upgrade ansible-lint yamllint", "deployment lint tool install"),
    ("yamllint .github Deployment/LocalCluster", "deployment YAML lint step"),
    ("ANSIBLE_CONFIG=Deployment/LocalCluster/ansible/ansible.cfg ansible-lint -c .ansible-lint.yml Deployment/LocalCluster/ansible", "deployment Ansible lint step"),
    ("python Deployment/LocalCluster/scripts/lib/read-deploy-setting.py app_image", "deployment image setting"),
    ("python Deployment/LocalCluster/scripts/lib/read-deploy-setting.py migration_bundle_name", "migration bundle setting"),
    ("dotnet restore", "restore step"),
    ("dotnet build --configuration Release --no-restore", "Release build step"),
    ("dotnet test --configuration Release --no-build", "test step"),
    ("dotnet ef migrations bundle", "migration bundle build"),
    ("docker build", "Docker image build"),
    ("if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'", "main-only artifact/image publish guard"),
    ("docker push \"${APP_IMAGE}:${{ github.sha }}\"", "immutable configured image push"),
]:
    if needle not in ci:
        fail(f".github/workflows/ci.yml: missing {why}")

for path, checks in {
    ".yamllint.yml": [
        ("extends: default", "default yamllint rule base"),
        ("max-spaces-inside: 1", "ansible-lint compatible braces rule"),
        ("min-spaces-from-content: 1", "ansible-lint compatible comments rule"),
        ("comments-indentation: false", "ansible-lint compatible comment indentation rule"),
        ("line-length: disable", "long deployment command tolerance"),
        ("new-lines: disable", "Windows checkout line-ending tolerance"),
        ("forbid-explicit-octal: true", "ansible-lint compatible octal rule"),
        ("forbid-implicit-octal: true", "ansible-lint compatible octal rule"),
        ("truthy: disable", "GitHub Actions on-key tolerance"),
    ],
    ".ansible-lint.yml": [
        ("profile: basic", "basic ansible-lint profile"),
        ("use_default_rules: true", "default ansible-lint rules enabled"),
    ],
}.items():
    text = read(path)
    for needle, why in checks:
        if needle not in text:
            fail(f"{path}: missing {why}")
if "${APP_IMAGE}:latest" in ci or "docker push \"${APP_IMAGE}:latest\"" in ci:
    fail(".github/workflows/ci.yml: CI must publish only immutable Git SHA image tags")

deploy_lan = read(".github/workflows/cd-localcluster.yml")
for needle, why in [
    ("name: CD - Deploy LocalCluster", "CD workflow name"),
    ("actions: read", "permission to inspect CI workflow runs"),
    ("environment:", "GitHub deployment environment"),
    ("LOCALCLUSTER_ENVIRONMENT", "optional side-by-side GitHub environment variable"),
    ("concurrency:", "deployment concurrency guard"),
    ("group: cd-localcluster", "CD concurrency group"),
    ("LOCALCLUSTER_RUNNER_LABEL", "optional side-by-side runner label variable"),
    ("localcluster", "shared LocalCluster runner label"),
    ("Require main branch", "main branch deployment guard"),
    ("refs/heads/main", "main branch deployment guard"),
    ("python Deployment/LocalCluster/scripts/lib/read-deploy-setting.py app_image", "deployment image setting"),
    ("python Deployment/LocalCluster/scripts/lib/read-deploy-setting.py public_hostname", "public hostname setting"),
    ("echo \"APP_VERSION=${GITHUB_SHA}\"", "automatic selected-ref image tag"),
    ("python Deployment/LocalCluster/scripts/lib/find-successful-ci-run.py", "successful CI gate"),
    ("CI_RUN_ID=", "CI run id export"),
    ("docker manifest inspect \"${APP_IMAGE}:${APP_VERSION}\"", "image existence check"),
    ("uses: actions/download-artifact@v4", "CI migration artifact download"),
    ("run-id: ${{ env.CI_RUN_ID }}", "download artifact from matching CI run"),
    ("chmod 0750 \"artifacts/migrations/${MIGRATION_BUNDLE_NAME}\"", "restore migration bundle execute bit"),
    ("bash Deployment/LocalCluster/scripts/preflight.sh deploy", "deploy preflight"),
    ("with-deploy-lock.sh", "cross-repo deployment lock"),
    ("-e app_version=${APP_VERSION}", "selected-ref image deployment"),
    ("${{ github.workspace }}/artifacts/migrations/${MIGRATION_BUNDLE_NAME}", "absolute migration bundle path"),
    ("https://${PUBLIC_HOSTNAME}/health/ready", "public readiness verification"),
    ("rm -f \"/tmp/${APP_NAME}_ansible_vault_password\"", "vault password file cleanup"),
]:
    if needle not in deploy_lan:
        fail(f".github/workflows/cd-localcluster.yml: missing {why}")
if "image_tag" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: manual image_tag input should not be required")
if "Deploy Ship To LAN" in deploy_lan or "Deploy App To LAN" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: workflow name must be explicitly CD-oriented")
if "dotnet ef migrations bundle" in deploy_lan or "dotnet restore" in deploy_lan or "dotnet tool restore" in deploy_lan:
    fail(".github/workflows/cd-localcluster.yml: CD must consume CI artifacts instead of rebuilding them")

find_ci = read("Deployment/LocalCluster/scripts/lib/find-successful-ci-run.py")
for needle, why in [
    ("GITHUB_REPOSITORY", "repository input"),
    ("GITHUB_SHA", "commit input"),
    ("GITHUB_TOKEN", "GitHub token input"),
    ("actions/workflows", "workflow runs API"),
    ("conclusion\") == \"success\"", "successful CI conclusion requirement"),
    ("event\") != \"pull_request\"", "pull request run exclusion"),
]:
    if needle not in find_ci:
        fail(f"Deployment/LocalCluster/scripts/lib/find-successful-ci-run.py: missing {why}")


prepare = read("Deployment/LocalCluster/ansible/playbooks/PrepareFreshLinuxMachine.yml")
role_order = ["mint_base", "ssh_hardening", "docker", "firewall"]
positions = [prepare.find(f"- {role}") for role in role_order]
if any(pos < 0 for pos in positions) or positions != sorted(positions):
    fail("PrepareFreshLinuxMachine.yml: roles must run mint_base, ssh_hardening, docker, firewall")

site = read("Deployment/LocalCluster/ansible/playbooks/site.yml")
for needle, why in [
    ("hosts: node_db", "node_db deployment phase"),
    ("hosts: load_balancer", "load balancer deployment phase"),
    ("hosts: app_servers", "app server deployment phase"),
    ("Stop app containers before migration", "migration downtime step"),
    ("Create pre-migration database backup", "pre-migration backup"),
    ("Run migration bundle", "migration execution"),
]:
    if needle not in site:
        fail(f"Deployment/LocalCluster/ansible/playbooks/site.yml: missing {why}")

for path, checks in {
    "Deployment/LocalCluster/ansible/roles/mint_base/tasks/main.yml": [
        ("name: deploy", "deploy user creation"),
        ("NOPASSWD:ALL", "passwordless sudo for automation"),
        ("authorized_keys", "deploy SSH public key installation"),
        ("deploy_private_key_file", "control-node private key installation"),
        ("inventory_hostname in groups[\"load_balancer\"]", "private key limited to control node"),
        ("known_hosts", "control-node SSH host key setup"),
        ("ssh-keyscan", "deployment node host key scan"),
        ("path: \"{{ deploy_root }}\"", "deployment root creation"),
    ],
    "Deployment/LocalCluster/ansible/roles/docker/tasks/main.yml": [
        ("UBUNTU_CODENAME", "Linux Mint Ubuntu base codename detection"),
        ("This deployment supports only x86_64/amd64 Linux machines.", "amd64-only Docker guard"),
        ("arch=amd64", "amd64 Docker apt repository"),
        ("docker-compose-plugin", "Docker Compose plugin"),
        ("groups: docker", "deploy docker group membership"),
    ],
    "Deployment/LocalCluster/ansible/roles/firewall/tasks/main.yml": [
        ("ufw allow OpenSSH", "SSH firewall rule"),
        ("{{ app_name }}-docker-user-firewall.service", "Docker published-port firewall service"),
        ("groups[\"node_db\"]", "node_db firewall targeting"),
        ("to any port {{ postgres_port }}", "PostgreSQL firewall port"),
        ("to any port {{ redis_port }}", "Redis firewall port"),
    ],
    "Deployment/LocalCluster/ansible/roles/app/templates/app.env.j2": [
        ("APP_NAME={{ app_name }}", "app identity env marker"),
        ("APP_PORT={{ app_port }}", "app port env rendering"),
        ("POSTGRES_PORT={{ postgres_port }}", "PostgreSQL port env rendering"),
        ("REDIS_PORT={{ redis_port }}", "Redis port env rendering"),
    ],
    "Deployment/LocalCluster/ansible/roles/postgres/templates/node-db.env.j2": [
        ("APP_NAME={{ app_name }}", "node-db app identity env marker"),
        ("POSTGRES_PORT={{ postgres_port }}", "PostgreSQL port env rendering"),
        ("REDIS_PORT={{ redis_port }}", "Redis port env rendering"),
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
    ],
    "Deployment/LocalCluster/ansible/roles/caddy/templates/app.caddy.j2": [
        ("http://{{ public_hostname }}", "hostname-based Caddy listener for side-by-side apps"),
        ("bind 127.0.0.1", "loopback-only Caddy listener"),
        ("health_uri /health/ready", "readiness health check"),
        ("lb_policy cookie {{ app_name }}_lb", "sticky sessions for Blazor Server"),
    ],
}.items():
    text = read(path)
    for needle, why in checks:
        if needle not in text:
            fail(f"{path}: missing {why}")
if "iptables -F DOCKER-USER" in read("Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2"):
    fail("Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2: must not flush shared DOCKER-USER chain")


preflight = read("Deployment/LocalCluster/scripts/preflight.sh")
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
]:
    if needle not in preflight:
        fail(f"Deployment/LocalCluster/scripts/preflight.sh: missing {why}")

check_port_collisions = read("Deployment/LocalCluster/scripts/check-port-collisions.sh")
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
        fail(f"Deployment/LocalCluster/scripts/check-port-collisions.sh: missing {why}")

deploy_lock = read("Deployment/LocalCluster/scripts/support/with-deploy-lock.sh")
for needle, why in [
    ("mkdir \"$LOCK_DIR\"", "directory-based cross-repo deployment lock"),
    ("LOCALCLUSTER_DEPLOY_LOCK_DIR", "configurable lock directory"),
    ("LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS", "configurable lock timeout"),
    ("LOCALCLUSTER_DEPLOY_LOCK_STALE_SECONDS", "stale lock cleanup"),
    ("created_epoch", "stale lock age marker"),
]:
    if needle not in deploy_lock:
        fail(f"Deployment/LocalCluster/scripts/support/with-deploy-lock.sh: missing {why}")

node_main_deploy_lock = read("Deployment/LocalCluster/scripts/support/with-node-main-deploy-lock.sh")
for needle, why in [
    ("ansible-inventory", "node-main lookup from inventory"),
    ("node-main", "node-main remote lock target"),
    ("ssh", "remote lock transport"),
    ("try_acquire_lock", "remote lock acquisition"),
    ("LOCALCLUSTER_DEPLOY_LOCK_DIR", "shared lock directory"),
    ("LOCK_STALE_SECONDS", "stale lock cleanup"),
]:
    if needle not in node_main_deploy_lock:
        fail(f"Deployment/LocalCluster/scripts/support/with-node-main-deploy-lock.sh: missing {why}")
require_contains(
    "Deployment/LocalCluster/scripts/deploy.sh",
    "support/with-node-main-deploy-lock.sh",
    "manual deploy node-main lock wrapper",
)

for path in [
    "Deployment/LocalCluster/scripts/support/ping-fresh-machines.sh",
    "Deployment/LocalCluster/scripts/prepare-fresh-linux-machines.sh",
]:
    require_contains(path, "ANSIBLE_HOST_KEY_CHECKING=False", "bootstrap host-key bypass for password SSH")

check_vault = read("Deployment/LocalCluster/scripts/check-vault.sh")
for needle, why in [
    ("ansible-vault view", "vault decrypt validation"),
    ("REPLACE_WITH", "placeholder rejection"),
    ("validate-vault.py", "strict vault value validation"),
]:
    if needle not in check_vault:
        fail(f"Deployment/LocalCluster/scripts/check-vault.sh: missing {why}")

validate_vault = read("Deployment/LocalCluster/scripts/lib/validate-vault.py")
for needle, why in [
    ("duplicate key", "duplicate vault key rejection"),
    ("DOTENV_SAFE_PASSWORD", "dotenv-safe DB/Redis password validation"),
    ("vault_cloudflare_tunnel_token", "Cloudflare token key validation"),
    ("vault_ghcr_token", "GHCR token key validation"),
    ("unknown key", "unknown vault key rejection"),
]:
    if needle not in validate_vault:
        fail(f"Deployment/LocalCluster/scripts/lib/validate-vault.py: missing {why}")

setup_secrets = read("Deployment/LocalCluster/scripts/setup-secrets.sh")
for needle, why in [
    ("gh secret set ANSIBLE_VAULT_PASSWORD", "GitHub vault password secret automation"),
    ("ansible-vault edit", "vault editing"),
    ("check-vault.sh", "vault validation"),
]:
    if needle not in setup_secrets:
        fail(f"Deployment/LocalCluster/scripts/setup-secrets.sh: missing {why}")

verify_bootstrap = read("Deployment/LocalCluster/scripts/verify-bootstrap.sh")
for needle, why in [
    ("status.sh\" bootstrap", "bootstrap status check"),
    ("preflight.sh\" bootstrap", "bootstrap preflight check"),
    ("support/ping-fresh-machines.sh", "fresh-machine ping check"),
    ("bootstrap verification ok", "clear success line"),
]:
    if needle not in verify_bootstrap:
        fail(f"Deployment/LocalCluster/scripts/verify-bootstrap.sh: missing {why}")

verify_deployment = read("Deployment/LocalCluster/scripts/verify-deployment.sh")
for needle, why in [
    ("public_hostname", "public hostname setting"),
    ("app_port", "app port setting"),
    ("postgres_port", "PostgreSQL port setting"),
    ("redis_port", "Redis port setting"),
    ("deploy_root", "deploy root setting"),
    ("curl -fsS \"https://${PUBLIC_HOSTNAME}/health/ready\"", "public health check"),
    ("http://127.0.0.1:${APP_PORT}/health/ready", "IPv4 app-node health check"),
    ("-H 'Host: ${PUBLIC_HOSTNAME}' http://127.0.0.1/health/ready", "hostname-aware Caddy health check"),
    ("sport = :${POSTGRES_PORT}", "PostgreSQL host port check"),
    ("sport = :${REDIS_PORT}", "Redis host port check"),
    ("ansible app_servers", "app-server checks"),
    ("ansible node_db", "database-node checks"),
    ("ansible load_balancer", "load-balancer checks"),
    ("deployment verification ok", "clear success line"),
]:
    if needle not in verify_deployment:
        fail(f"Deployment/LocalCluster/scripts/verify-deployment.sh: missing {why}")
if "http://localhost" in verify_deployment:
    fail("Deployment/LocalCluster/scripts/verify-deployment.sh: use 127.0.0.1 instead of localhost for local health checks")

runner_setup = read("Deployment/LocalCluster/scripts/install-github-runner.sh")
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
    ("/opt/actions-runner-${APP_NAME}", "app-specific runner directory"),
    ("sudo ./svc.sh install deploy", "runner service install as deploy"),
]:
    if needle not in runner_setup:
        fail(f"Deployment/LocalCluster/scripts/install-github-runner.sh: missing {why}")
runner_configured_pos = runner_setup.find("RUNNER_CONFIGURED=")
runner_token_pos = runner_setup.find('RUNNER_TOKEN="$(gh api')
if runner_configured_pos < 0 or runner_token_pos < 0 or runner_token_pos < runner_configured_pos:
    fail("Deployment/LocalCluster/scripts/install-github-runner.sh: check remote runner state before requesting a runner token")
if "RUNNER_TOKEN='$RUNNER_TOKEN'" in runner_setup or 'RUNNER_TOKEN="$RUNNER_TOKEN"' in runner_setup:
    fail("Deployment/LocalCluster/scripts/install-github-runner.sh: runner token must not be passed in the ssh command arguments")
for forbidden in ["RUNNER_ARCH=", "aarch64", "arm64", "armv7l", "armv6l"]:
    if forbidden in runner_setup:
        fail(f"Deployment/LocalCluster/scripts/install-github-runner.sh: contains forbidden multi-architecture runner logic: {forbidden}")

setup_cloudflare = read("Deployment/LocalCluster/scripts/setup-cloudflare-tunnel.sh")
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
    ("vault_cloudflare_tunnel_token", "vault token output"),
]:
    if needle not in setup_cloudflare:
        fail(f"Deployment/LocalCluster/scripts/setup-cloudflare-tunnel.sh: missing {why}")
if "def read_simple_yaml_value" in setup_cloudflare:
    fail("Deployment/LocalCluster/scripts/setup-cloudflare-tunnel.sh: use deploy_settings.py instead of a local all.yml parser")
for normal_path in [
    "Deployment/LocalCluster/scripts/preflight.sh",
    "Deployment/LocalCluster/scripts/status.sh",
    "Deployment/LocalCluster/scripts/setup-secrets.sh",
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
