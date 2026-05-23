#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
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
    ".github/workflows/deploy-lan.yml",
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
    "Deployment/LocalCluster/scripts/backup-db.sh",
    "Deployment/LocalCluster/scripts/bootstrap-node.sh",
    "Deployment/LocalCluster/scripts/check-vault.sh",
    "Deployment/LocalCluster/scripts/deploy.sh",
    "Deployment/LocalCluster/scripts/deploy_settings.py",
    "Deployment/LocalCluster/scripts/discover-machines.sh",
    "Deployment/LocalCluster/scripts/generate-inventory.py",
    "Deployment/LocalCluster/scripts/generate-inventory.sh",
    "Deployment/LocalCluster/scripts/install-ansible.sh",
    "Deployment/LocalCluster/scripts/install-github-runner.sh",
    "Deployment/LocalCluster/scripts/ping-fresh-machines.sh",
    "Deployment/LocalCluster/scripts/preflight.sh",
    "Deployment/LocalCluster/scripts/prepare-fresh-linux-machines.sh",
    "Deployment/LocalCluster/scripts/setup-cloudflare-tunnel.sh",
    "Deployment/LocalCluster/scripts/setup-control-machine.sh",
    "Deployment/LocalCluster/scripts/setup-secrets.sh",
    "Deployment/LocalCluster/scripts/restore-db.sh",
    "Deployment/LocalCluster/scripts/read-deploy-setting.py",
    "Deployment/LocalCluster/scripts/status.sh",
    "Deployment/LocalCluster/scripts/validate-deploy-settings.py",
    "Deployment/LocalCluster/scripts/validate-vault.py",
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
    "Deployment/LocalCluster/.deploy.local.env.example",
    "Deployment/LocalCluster/scripts/discover-node.sh",
    "Deployment/LocalCluster/scripts/health-check.sh",
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
    if rel == "Deployment/LocalCluster/scripts/audit_deployment.py":
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
        fail(f"{rel}: use Deployment/LocalCluster/scripts/install-ansible.sh instead of distro Ansible")
    for forbidden in [".deploy.local", "discover-node", "health-check"]:
        if forbidden in text:
            fail(f"{rel}: contains stale deployment reference: {forbidden}")
    for stale_setting in [
        "caddy_sticky_cookie_name",
        "caddy_bind_address",
        "caddy_http_port",
        "postgres_port",
        "redis_port",
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
        [sys.executable, str(ROOT / "Deployment/LocalCluster/scripts/validate-deploy-settings.py")],
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
generate_inventory = read("Deployment/LocalCluster/scripts/generate-inventory.py")
for needle, why in [
    ("REQUIRED_NODES = [\"node-main\", \"node-app1\", \"node-app2\", \"node-db\"]", "required node list"),
    ("import ipaddress", "strict IP address validation"),
    ("from deploy_settings import load_settings", "shared deployment settings reader"),
    ("unexpected node", "unexpected node rejection"),
    ("duplicate IP address", "duplicate IP rejection"),
    ("duplicate MAC address", "duplicate MAC rejection"),
    ("node_db:", "node_db inventory group rendering"),
    ("render_bootstrap_hosts", "bootstrap inventory rendering"),
    ("install_user", "install user support"),
]:
    if needle not in generate_inventory:
        fail(f"Deployment/LocalCluster/scripts/generate-inventory.py: missing {why}")
if "def read_simple_group_var" in generate_inventory:
    fail("Deployment/LocalCluster/scripts/generate-inventory.py: use deploy_settings.py instead of a local all.yml parser")

for path, checks in {
    "Deployment/LocalCluster/scripts/read-deploy-setting.py": [
        ("from deploy_settings import load_settings", "shared deployment settings reader"),
        ("load_settings(settings_path, validate_file=True)", "settings validation before read"),
    ],
    "Deployment/LocalCluster/scripts/validate-deploy-settings.py": [
        ("from deploy_settings import load_settings", "shared deployment settings validator"),
    ],
    "Deployment/LocalCluster/scripts/deploy_settings.py": [
        ("REQUIRED_KEYS", "required all.yml keys"),
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
    ("Redis__Configuration", "Redis configuration injection"),
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
    ("REDIS_PASSWORD", "Redis secret injection"),
]:
    if needle not in node_db_compose:
        fail(f"Deployment/LocalCluster/compose/node-db/docker-compose.yml: missing {why}")


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
    "Deployment/LocalCluster/scripts/install-ansible.sh",
    "sshpass",
    "sshpass for Ansible password bootstrap",
)
require_contains(
    "Deployment/LocalCluster/scripts/install-ansible.sh",
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
    ("python Deployment/LocalCluster/scripts/audit_deployment.py", "deployment audit step"),
    ("python Deployment/LocalCluster/scripts/read-deploy-setting.py app_image", "deployment image setting"),
    ("python Deployment/LocalCluster/scripts/read-deploy-setting.py migration_bundle_name", "migration bundle setting"),
    ("dotnet restore", "restore step"),
    ("dotnet build --configuration Release --no-restore", "Release build step"),
    ("dotnet test --configuration Release --no-build", "test step"),
    ("dotnet ef migrations bundle", "migration bundle build"),
    ("docker build", "Docker image build"),
    ("if: github.event_name != 'pull_request'", "no PR artifact/image push guard"),
    ("docker push \"${APP_IMAGE}:${{ github.sha }}\"", "immutable configured image push"),
]:
    if needle not in ci:
        fail(f".github/workflows/ci.yml: missing {why}")
if "${APP_IMAGE}:latest" in ci or "docker push \"${APP_IMAGE}:latest\"" in ci:
    fail(".github/workflows/ci.yml: CI must publish only immutable Git SHA image tags")

deploy_lan = read(".github/workflows/deploy-lan.yml")
for needle, why in [
    ("name: Deploy App To LAN", "generic deployment workflow name"),
    ("concurrency:", "deployment concurrency guard"),
    ("runs-on: [self-hosted, linux, x64, homelab]", "self-hosted LAN runner targeting"),
    ("python Deployment/LocalCluster/scripts/read-deploy-setting.py app_image", "deployment image setting"),
    ("python Deployment/LocalCluster/scripts/read-deploy-setting.py public_hostname", "public hostname setting"),
    ("echo \"APP_VERSION=${GITHUB_SHA}\"", "automatic selected-ref image tag"),
    ("docker manifest inspect \"${APP_IMAGE}:${APP_VERSION}\"", "image existence check"),
    ("bash Deployment/LocalCluster/scripts/preflight.sh deploy", "deploy preflight"),
    ("-e app_version=${APP_VERSION}", "selected-ref image deployment"),
    ("${{ github.workspace }}/artifacts/migrations/${MIGRATION_BUNDLE_NAME}", "absolute migration bundle path"),
    ("https://${PUBLIC_HOSTNAME}/health/ready", "public readiness verification"),
    ("rm -f \"/tmp/${APP_NAME}_ansible_vault_password\"", "vault password file cleanup"),
]:
    if needle not in deploy_lan:
        fail(f".github/workflows/deploy-lan.yml: missing {why}")
if "image_tag" in deploy_lan:
    fail(".github/workflows/deploy-lan.yml: manual image_tag input should not be required")
if "Deploy Ship To LAN" in deploy_lan:
    fail(".github/workflows/deploy-lan.yml: workflow name must not be app-bound")


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
        ("to any port 5432", "PostgreSQL firewall port"),
        ("to any port 6379", "Redis firewall port"),
    ],
    "Deployment/LocalCluster/ansible/roles/app/templates/app.env.j2": [
        ("APP_PORT={{ app_port }}", "app port env rendering"),
    ],
    "Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2": [
        ("DOCKER-USER", "Docker firewall chain"),
        ("--ctorigdstport {{ app_port }}", "app port restriction"),
        ("--ctorigdstport 5432", "PostgreSQL port restriction"),
        ("--ctorigdstport 6379", "Redis port restriction"),
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
        ("127.0.0.1:80", "local-only Caddy listener for Cloudflare Tunnel"),
        ("health_uri /health/ready", "readiness health check"),
        ("lb_policy cookie {{ app_name }}_lb", "sticky sessions for Blazor Server"),
    ],
}.items():
    text = read(path)
    for needle, why in checks:
        if needle not in text:
            fail(f"{path}: missing {why}")


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
]:
    if needle not in preflight:
        fail(f"Deployment/LocalCluster/scripts/preflight.sh: missing {why}")

for path in ["Deployment/LocalCluster/scripts/ping-fresh-machines.sh", "Deployment/LocalCluster/scripts/prepare-fresh-linux-machines.sh"]:
    require_contains(path, "ANSIBLE_HOST_KEY_CHECKING=False", "bootstrap host-key bypass for password SSH")

check_vault = read("Deployment/LocalCluster/scripts/check-vault.sh")
for needle, why in [
    ("ansible-vault view", "vault decrypt validation"),
    ("REPLACE_WITH", "placeholder rejection"),
    ("validate-vault.py", "strict vault value validation"),
]:
    if needle not in check_vault:
        fail(f"Deployment/LocalCluster/scripts/check-vault.sh: missing {why}")

validate_vault = read("Deployment/LocalCluster/scripts/validate-vault.py")
for needle, why in [
    ("duplicate key", "duplicate vault key rejection"),
    ("DOTENV_SAFE_PASSWORD", "dotenv-safe DB/Redis password validation"),
    ("vault_cloudflare_tunnel_token", "Cloudflare token key validation"),
    ("vault_ghcr_token", "GHCR token key validation"),
    ("unknown key", "unknown vault key rejection"),
]:
    if needle not in validate_vault:
        fail(f"Deployment/LocalCluster/scripts/validate-vault.py: missing {why}")

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
    ("ping-fresh-machines.sh", "fresh-machine ping check"),
    ("bootstrap verification ok", "clear success line"),
]:
    if needle not in verify_bootstrap:
        fail(f"Deployment/LocalCluster/scripts/verify-bootstrap.sh: missing {why}")

verify_deployment = read("Deployment/LocalCluster/scripts/verify-deployment.sh")
for needle, why in [
    ("public_hostname", "public hostname setting"),
    ("app_port", "app port setting"),
    ("deploy_root", "deploy root setting"),
    ("curl -fsS \"https://${PUBLIC_HOSTNAME}/health/ready\"", "public health check"),
    ("http://127.0.0.1:${APP_PORT}/health/ready", "IPv4 app-node health check"),
    ("http://127.0.0.1/health/ready", "IPv4 Caddy health check"),
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
    ("--labels homelab", "runner label configuration"),
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
    ".github/workflows/deploy-lan.yml",
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
