#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
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
    ".github/workflows/ci.yml",
    ".github/workflows/deploy-lan.yml",
    ".config/dotnet-tools.json",
    ".gitignore",
    "Deployment/machines.example.yml",
    "Deployment/inventory/prod/hosts.yml",
    "Deployment/inventory/prod/group_vars/all.yml",
    "Deployment/inventory/prod/group_vars/app_servers.yml",
    "Deployment/inventory/prod/group_vars/load_balancer.yml",
    "Deployment/inventory/prod/group_vars/node_db.yml",
    "Deployment/inventory/prod/vault.example.yml",
    "Deployment/inventory/prod/host_vars/node-app1.yml",
    "Deployment/inventory/prod/host_vars/node-app2.yml",
    "Deployment/inventory/prod/host_vars/node-db.yml",
    "Deployment/inventory/prod/host_vars/node-main.yml",
    "Deployment/ansible/ansible.cfg",
    "Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml",
    "Deployment/ansible/playbooks/node-db.yml",
    "Deployment/ansible/playbooks/site.yml",
    "Deployment/ansible/roles/app/tasks/main.yml",
    "Deployment/ansible/roles/app/templates/app.env.j2",
    "Deployment/ansible/roles/caddy/tasks/main.yml",
    "Deployment/ansible/roles/caddy/templates/app.caddy.j2",
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "Deployment/ansible/roles/docker/tasks/main.yml",
    "Deployment/ansible/roles/firewall/tasks/main.yml",
    "Deployment/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2",
    "Deployment/ansible/roles/firewall/templates/app-docker-user-firewall.service.j2",
    "Deployment/ansible/roles/mint_base/tasks/main.yml",
    "Deployment/ansible/roles/postgres/tasks/main.yml",
    "Deployment/ansible/roles/postgres/templates/node-db.env.j2",
    "Deployment/ansible/roles/redis/tasks/main.yml",
    "Deployment/ansible/roles/ssh_hardening/tasks/main.yml",
    "Deployment/compose/app-server/docker-compose.yml",
    "Deployment/compose/node-db/docker-compose.yml",
    "Deployment/scripts/backup-db.sh",
    "Deployment/scripts/bootstrap-node.sh",
    "Deployment/scripts/check-vault.sh",
    "Deployment/scripts/deploy.sh",
    "Deployment/scripts/generate-inventory.py",
    "Deployment/scripts/generate-inventory.sh",
    "Deployment/scripts/install-ansible.sh",
    "Deployment/scripts/install-github-runner.sh",
    "Deployment/scripts/preflight.sh",
    "Deployment/scripts/prepare-fresh-linux-machines.sh",
    "Deployment/scripts/setup-cloudflare-tunnel.sh",
    "Deployment/scripts/setup-control-machine.sh",
    "Deployment/scripts/setup-secrets.sh",
    "Deployment/scripts/restore-db.sh",
    "Deployment/scripts/health-check.sh",
    "Deployment/scripts/read-deploy-setting.py",
    "Deployment/scripts/status.sh",
    "BlazorAutoApp/Program.cs",
    "BlazorAutoApp/BlazorAutoApp.csproj",
]
for file in required_files:
    require_file(file)


tracked = tracked_files()
for path in [
    ".env",
    "secrets.env",
    "Deployment/.deploy.local.env",
    "Deployment/machines.yml",
    "Deployment/inventory/prod/bootstrap-hosts.yml",
]:
    if path in tracked:
        fail(f"local or secret file must not be tracked: {path}")

for path in tracked:
    if re.search(r"(^|/)(__pycache__|\.pytest_cache)(/|$)", path) or re.search(
        r"\.(pyc|pyo|pyd|pfx|tmp|log)$", path
    ):
        fail(f"generated/cache/secret-like file must not be tracked: {path}")


for path in deployment_text_files():
    rel = path.relative_to(ROOT).as_posix()
    if rel == "Deployment/scripts/audit_deployment.py":
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
        fail(f"{rel}: use Deployment/scripts/install-ansible.sh instead of distro Ansible")


all_vars = read("Deployment/inventory/prod/group_vars/all.yml")
cloudflared_match = re.search(r"^cloudflared_version:\s*(\S+)\s*$", all_vars, re.MULTILINE)
if not cloudflared_match:
    fail("Deployment/inventory/prod/group_vars/all.yml: missing cloudflared_version")
elif cloudflared_match.group(1) == "latest":
    fail("cloudflared_version must be pinned, not latest")

require_contains(
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_version != \"latest\"",
    "cloudflared pinned-version guard",
)
require_contains(
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared --version",
    "cloudflared installed-version verification",
)
require_contains(
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "This deployment supports only x86_64/amd64 Linux machines.",
    "amd64-only cloudflared guard",
)
require_contains(
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared-linux-amd64.deb",
    "amd64 cloudflared package",
)
require_contains(
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "tunnel-token.sha256",
    "Cloudflare tunnel token change marker",
)
require_contains(
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared service uninstall",
    "Cloudflare tunnel token rotation handling",
)
require_not_contains(
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "cloudflared_deb_arch",
    "cloudflared multi-architecture package mapping",
)


ansible_cfg = read("Deployment/ansible/ansible.cfg")
for needle, why in [
    ("inventory = ../inventory/prod/hosts.yml", "default production inventory"),
    ("roles_path = roles", "local roles path"),
    ("interpreter_python = auto_silent", "Python interpreter auto-detection"),
]:
    if needle not in ansible_cfg:
        fail(f"Deployment/ansible/ansible.cfg: missing {why}")


hosts = read("Deployment/inventory/prod/hosts.yml")
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
        fail(f"Deployment/inventory/prod/hosts.yml: missing {why}")
generate_inventory = read("Deployment/scripts/generate-inventory.py")
for needle, why in [
    ("REQUIRED_NODES = [\"node-main\", \"node-app1\", \"node-app2\", \"node-db\"]", "required node list"),
    ("import ipaddress", "strict IP address validation"),
    ("unexpected node", "unexpected node rejection"),
    ("duplicate IP address", "duplicate IP rejection"),
    ("duplicate MAC address", "duplicate MAC rejection"),
    ("node_db:", "node_db inventory group rendering"),
    ("render_bootstrap_hosts", "bootstrap inventory rendering"),
    ("install_user", "install user support"),
]:
    if needle not in generate_inventory:
        fail(f"Deployment/scripts/generate-inventory.py: missing {why}")


deploy_app_compose = read("Deployment/compose/app-server/docker-compose.yml")
for needle, why in [
    ("${APP_IMAGE}:${APP_VERSION}", "immutable image variables"),
    ('Database__RunMigrationsAtStartup: "false"', "production startup migrations disabled"),
    ("ConnectionStrings__DefaultConnection", "database connection injection"),
    ("Redis__Configuration", "Redis configuration injection"),
]:
    if needle not in deploy_app_compose:
        fail(f"Deployment/compose/app-server/docker-compose.yml: missing {why}")
for local_only in ["redisinsight", "datalust/seq", "build:"]:
    if local_only in deploy_app_compose:
        fail(f"Deployment/compose/app-server/docker-compose.yml: contains local-only deployment content: {local_only}")

node_db_compose = read("Deployment/compose/node-db/docker-compose.yml")
for needle, why in [
    ("postgres:", "PostgreSQL service"),
    ("redis:", "Redis service"),
    ("POSTGRES_PASSWORD", "PostgreSQL secret injection"),
    ("REDIS_PASSWORD", "Redis secret injection"),
]:
    if needle not in node_db_compose:
        fail(f"Deployment/compose/node-db/docker-compose.yml: missing {why}")


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
    "Deployment/scripts/install-ansible.sh",
    "sshpass",
    "sshpass for Ansible password bootstrap",
)


ci = read(".github/workflows/ci.yml")
for needle, why in [
    ("python Deployment/scripts/audit_deployment.py", "deployment audit step"),
    ("python Deployment/scripts/read-deploy-setting.py app_image", "deployment image setting"),
    ("python Deployment/scripts/read-deploy-setting.py migration_bundle_name", "migration bundle setting"),
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
    ("python Deployment/scripts/read-deploy-setting.py app_image", "deployment image setting"),
    ("python Deployment/scripts/read-deploy-setting.py public_hostname", "public hostname setting"),
    ("echo \"APP_VERSION=${GITHUB_SHA}\"", "automatic selected-ref image tag"),
    ("docker manifest inspect \"${APP_IMAGE}:${APP_VERSION}\"", "image existence check"),
    ("bash Deployment/scripts/preflight.sh deploy", "deploy preflight"),
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


prepare = read("Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml")
role_order = ["mint_base", "ssh_hardening", "docker", "firewall"]
positions = [prepare.find(f"- {role}") for role in role_order]
if any(pos < 0 for pos in positions) or positions != sorted(positions):
    fail("PrepareFreshLinuxMachine.yml: roles must run mint_base, ssh_hardening, docker, firewall")

site = read("Deployment/ansible/playbooks/site.yml")
for needle, why in [
    ("hosts: node_db", "node_db deployment phase"),
    ("hosts: load_balancer", "load balancer deployment phase"),
    ("hosts: app_servers", "app server deployment phase"),
    ("Stop app containers before migration", "migration downtime step"),
    ("Create pre-migration database backup", "pre-migration backup"),
    ("Run migration bundle", "migration execution"),
]:
    if needle not in site:
        fail(f"Deployment/ansible/playbooks/site.yml: missing {why}")

for path, checks in {
    "Deployment/ansible/roles/mint_base/tasks/main.yml": [
        ("name: deploy", "deploy user creation"),
        ("NOPASSWD:ALL", "passwordless sudo for automation"),
        ("authorized_keys", "deploy SSH public key installation"),
        ("deploy_private_key_file", "control-node private key installation"),
        ("inventory_hostname in groups[\"load_balancer\"]", "private key limited to control node"),
        ("known_hosts", "control-node SSH host key setup"),
        ("ssh-keyscan", "deployment node host key scan"),
        ("path: \"{{ deploy_root }}\"", "deployment root creation"),
    ],
    "Deployment/ansible/roles/docker/tasks/main.yml": [
        ("UBUNTU_CODENAME", "Linux Mint Ubuntu base codename detection"),
        ("This deployment supports only x86_64/amd64 Linux machines.", "amd64-only Docker guard"),
        ("arch=amd64", "amd64 Docker apt repository"),
        ("docker-compose-plugin", "Docker Compose plugin"),
        ("groups: docker", "deploy docker group membership"),
    ],
    "Deployment/ansible/roles/firewall/tasks/main.yml": [
        ("ufw allow OpenSSH", "SSH firewall rule"),
        ("{{ app_name }}-docker-user-firewall.service", "Docker published-port firewall service"),
        ("groups[\"node_db\"]", "node_db firewall targeting"),
    ],
    "Deployment/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2": [
        ("DOCKER-USER", "Docker firewall chain"),
        ("--ctorigdstport {{ app_port }}", "app port restriction"),
        ("--ctorigdstport {{ postgres_port }}", "PostgreSQL port restriction"),
        ("--ctorigdstport {{ redis_port }}", "Redis port restriction"),
    ],
    "Deployment/ansible/roles/app/tasks/main.yml": [
        ("docker compose up -d --pull always", "pull and start requested image"),
        ("http://127.0.0.1:{{ app_port }}/health/ready", "local readiness wait"),
    ],
    "Deployment/ansible/roles/postgres/tasks/main.yml": [
        ("compose/node-db/docker-compose.yml", "node-db compose source"),
        ("node-db.env.j2", "node-db env template"),
        ("backup-db.sh", "backup helper copy"),
        ("restore-db.sh", "restore helper copy"),
    ],
    "Deployment/ansible/roles/caddy/templates/app.caddy.j2": [
        ("health_uri /health/ready", "readiness health check"),
        ("lb_policy cookie", "sticky sessions for Blazor Server"),
    ],
}.items():
    text = read(path)
    for needle, why in checks:
        if needle not in text:
            fail(f"{path}: missing {why}")


preflight = read("Deployment/scripts/preflight.sh")
for needle, why in [
    ("REPLACE_WITH", "inventory placeholder detection"),
    ("ansible-inventory", "inventory parse check"),
    ("vault.yml", "vault existence check"),
    ("check-vault.sh", "deploy vault content check"),
]:
    if needle not in preflight:
        fail(f"Deployment/scripts/preflight.sh: missing {why}")

for path in ["Deployment/scripts/ping-fresh-machines.sh", "Deployment/scripts/prepare-fresh-linux-machines.sh"]:
    require_contains(path, "ANSIBLE_HOST_KEY_CHECKING=False", "bootstrap host-key bypass for password SSH")

check_vault = read("Deployment/scripts/check-vault.sh")
for needle, why in [
    ("ansible-vault view", "vault decrypt validation"),
    ("REPLACE_WITH", "placeholder rejection"),
    ("vault_cloudflare_tunnel_token", "Cloudflare token key validation"),
    ("vault_ghcr_token", "GHCR token key validation"),
]:
    if needle not in check_vault:
        fail(f"Deployment/scripts/check-vault.sh: missing {why}")

setup_secrets = read("Deployment/scripts/setup-secrets.sh")
for needle, why in [
    ("gh secret set ANSIBLE_VAULT_PASSWORD", "GitHub vault password secret automation"),
    ("ansible-vault edit", "vault editing"),
    ("check-vault.sh", "vault validation"),
]:
    if needle not in setup_secrets:
        fail(f"Deployment/scripts/setup-secrets.sh: missing {why}")

runner_setup = read("Deployment/scripts/install-github-runner.sh")
for needle, why in [
    ("actions/runners/registration-token", "runner registration token automation"),
    ("gh release view --repo actions/runner", "runner release lookup"),
    ("actions-runner-linux-x64", "x64 runner package"),
    ("this deployment supports only x86_64/amd64 node-main machines", "x64 runner guard"),
    ("RUNNER_TOKEN_Q", "runner token kept out of ssh command arguments"),
    ("unset RUNNER_TOKEN", "runner token unset after configuration"),
    ("--labels homelab", "runner label configuration"),
    ("sudo ./svc.sh install deploy", "runner service install as deploy"),
]:
    if needle not in runner_setup:
        fail(f"Deployment/scripts/install-github-runner.sh: missing {why}")
if "RUNNER_TOKEN='$RUNNER_TOKEN'" in runner_setup or 'RUNNER_TOKEN="$RUNNER_TOKEN"' in runner_setup:
    fail("Deployment/scripts/install-github-runner.sh: runner token must not be passed in the ssh command arguments")
for forbidden in ["RUNNER_ARCH=", "aarch64", "arm64", "armv7l", "armv6l"]:
    if forbidden in runner_setup:
        fail(f"Deployment/scripts/install-github-runner.sh: contains forbidden multi-architecture runner logic: {forbidden}")

setup_cloudflare = read("Deployment/scripts/setup-cloudflare-tunnel.sh")
for needle, why in [
    ("CLOUDFLARE_ACCOUNT_ID", "Cloudflare account id input"),
    ("CLOUDFLARE_ZONE_ID", "Cloudflare zone id input"),
    ("CLOUDFLARE_API_TOKEN", "Cloudflare API token input"),
    ("cloudflare_tunnel_name", "tunnel name read from deployment settings"),
    ("public_hostname", "public hostname read from deployment settings"),
    ("POST", "Cloudflare tunnel creation"),
    ("cfd_tunnel", "Cloudflare tunnel API endpoint"),
    ("configurations", "Cloudflare tunnel configuration endpoint"),
    ("dns_records", "Cloudflare DNS record endpoint"),
    ("vault_cloudflare_tunnel_token", "vault token output"),
]:
    if needle not in setup_cloudflare:
        fail(f"Deployment/scripts/setup-cloudflare-tunnel.sh: missing {why}")
for normal_path in [
    "Deployment/scripts/preflight.sh",
    "Deployment/scripts/status.sh",
    "Deployment/scripts/setup-secrets.sh",
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
