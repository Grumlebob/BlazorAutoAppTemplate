#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def fail(message: str) -> None:
    failures.append(message)


def require_file(path: str) -> None:
    if not exists(path):
        fail(f"missing required file: {path}")


def require_contains(path: str, needle: str, why: str) -> None:
    text = read(path)
    if needle not in text:
        fail(f"{path}: missing {why}: {needle}")


def require_regex(path: str, pattern: str, why: str) -> None:
    text = read(path)
    if not re.search(pattern, text, re.MULTILINE | re.DOTALL):
        fail(f"{path}: missing {why}")


def require_not_contains(path: str, needle: str, why: str) -> None:
    text = read(path)
    if needle in text:
        fail(f"{path}: contains forbidden {why}: {needle}")


def deployment_text_files() -> list[Path]:
    roots = [
        ROOT / "Deployment",
        ROOT / "Plans",
        ROOT / ".github",
    ]
    suffixes = {".md", ".yml", ".yaml", ".j2", ".sh", ".json", ".cs", ".csproj"}
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in suffixes:
                files.append(path)
    for path in [
        ROOT / "README.md",
        ROOT / "HowToRunLocally.md",
        ROOT / "HowToDeploy.md",
    ]:
        if path.exists():
            files.append(path)
    return files


failures: list[str] = []


required_files = [
    ".github/dependabot.yml",
    ".github/workflows/auto-merge-dependabot.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy-lan.yml",
    ".config/dotnet-tools.json",
    "README.md",
    "HowToRunLocally.md",
    "HowToDeploy.md",
    "Deployment/inventory/prod/hosts.yml",
    "Deployment/inventory/prod/group_vars/all.yml",
    "Deployment/inventory/prod/vault.example.yml",
    "Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml",
    "Deployment/ansible/playbooks/site.yml",
    "Deployment/ansible/ansible.cfg",
    "Deployment/ansible/roles/mint_base/tasks/main.yml",
    "Deployment/ansible/roles/docker/tasks/main.yml",
    "Deployment/ansible/roles/firewall/tasks/main.yml",
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "Deployment/ansible/roles/caddy/templates/ship.caddy.j2",
    "Deployment/ansible/roles/app/tasks/main.yml",
    "Deployment/compose/app-server/docker-compose.yml",
    "Deployment/compose/db-redis/docker-compose.yml",
    "Deployment/scripts/install-ansible.sh",
    "Deployment/scripts/preflight.sh",
    "Deployment/scripts/prepare-fresh-linux-machines.sh",
    "Deployment/scripts/deploy.sh",
    "Deployment/scripts/backup-db.sh",
    "Deployment/scripts/restore-db.sh",
    "Deployment/scripts/discover-node.sh",
    "Deployment/scripts/health-check.sh",
    "Plans/DEPLOYMENT_PLAN.md",
    "docker-compose.yml",
    "BlazorAutoApp/Program.cs",
    "BlazorAutoApp/BlazorAutoApp.csproj",
    "BlazorAutoApp.Test/TestingSetup/WebAppFactory.cs",
]
for file in required_files:
    require_file(file)


if exists(".github/workflows/BuildAndTest.yml"):
    fail("legacy duplicate CI workflow still exists: .github/workflows/BuildAndTest.yml")

removed_thin_docs = [
    "Deployment/README.md",
    "Deployment/topology.md",
    "Deployment/cloudflare/README.md",
    "Deployment/secrets/README.md",
    "Deployment/secrets/.gitignore",
    "Deployment/docs/install-machines-checklist.md",
    "Deployment/docs/runbook.md",
    "Deployment/docs/rollback.md",
    "Deployment/docs/backup-restore.md",
    "Deployment/docs/cloudflare.md",
    "Deployment/docs/ports-and-firewall.md",
]
for doc in removed_thin_docs:
    if exists(doc):
        fail(f"removed low-value deployment doc still exists: {doc}")

removed_doc_references = [
    "Deployment/README.md",
    "Deployment/docs/install-machines-checklist.md",
    "Deployment/topology.md",
    "Deployment/cloudflare/README.md",
    "Deployment/secrets/README.md",
    "HowToRun.md",
    "docs/ENV.md",
    "docker/README.md",
    "topology.md",
    "cloudflare/README.md",
    "secrets/README.md",
    "install-machines-checklist.md",
    "runbook.md",
    "rollback.md",
    "backup-restore.md",
    "cloudflare.md",
    "ports-and-firewall.md",
]

removed_root_docs = [
    "HowToRun.md",
    "docs/ENV.md",
    "docker/README.md",
]
for doc in removed_root_docs:
    if exists(doc):
        fail(f"removed duplicate root doc still exists: {doc}")

for path in (ROOT / "Deployment/scripts").glob("*.ps1"):
    fail(f"PowerShell deployment script remains in Linux deployment scripts: {path.relative_to(ROOT)}")


for path in deployment_text_files():
    rel = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8-sig")
    if "improveddb" in text or "/opt/improveddb" in text:
        fail(f"{rel}: stale improveddb reference")
    if "releases/latest" in text:
        fail(f"{rel}: unpinned GitHub release URL")
    if "sudo apt install -y ansible" in text or "sudo apt-get install -y ansible" in text:
        fail(f"{rel}: installs distro Ansible instead of Deployment/scripts/install-ansible.sh")
    if "cd Deployment/" in text:
        fail(f"{rel}: relative cd Deployment/... command; use <repo-root>/Deployment/...")
    if "BuildAndTest" in text:
        fail(f"{rel}: stale BuildAndTest workflow reference")
    for removed_doc in removed_doc_references:
        if removed_doc in text and rel != "Deployment/scripts/audit_deployment.py":
            fail(f"{rel}: stale reference to removed low-value deployment doc: {removed_doc}")


all_vars = read("Deployment/inventory/prod/group_vars/all.yml")
match = re.search(r"^cloudflared_version:\s*(\S+)\s*$", all_vars, re.MULTILINE)
if not match:
    fail("Deployment/inventory/prod/group_vars/all.yml: missing cloudflared_version")
elif match.group(1) == "latest":
    fail("cloudflared_version must not be latest")

require_not_contains(
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "releases/latest",
    "cloudflared latest release URL",
)
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

ansible_cfg = read("Deployment/ansible/ansible.cfg")
for needle, why in [
    ("inventory = ../inventory/prod/hosts.yml", "default production inventory"),
    ("roles_path = roles", "local roles path"),
    ("interpreter_python = auto_silent", "Python interpreter auto-detection"),
    ("pipelining = True", "SSH pipelining"),
]:
    if needle not in ansible_cfg:
        fail(f"ansible.cfg: missing {why}")


local_compose = read("docker-compose.yml")
deploy_app_compose = read("Deployment/compose/app-server/docker-compose.yml")
if "build:" not in local_compose:
    fail("docker-compose.yml: local compose should build the app locally")
if 'Database__RunMigrationsAtStartup: "true"' not in local_compose:
    fail("docker-compose.yml: local compose must enable startup migrations")
if "${APP_IMAGE}:${APP_VERSION}" not in deploy_app_compose:
    fail("Deployment app compose must use prebuilt immutable image variables")
if 'Database__RunMigrationsAtStartup: "false"' not in deploy_app_compose:
    fail("Deployment app compose must disable startup migrations")
if "ConnectionStrings__DefaultConnection" not in deploy_app_compose:
    fail("Deployment app compose must inject the DB connection string")
if "Redis__Configuration" not in deploy_app_compose:
    fail("Deployment app compose must inject Redis configuration")
for local_only in ["redisinsight", "datalust/seq"]:
    if local_only in deploy_app_compose:
        fail(f"Deployment app compose contains local-only service/image: {local_only}")


program = read("BlazorAutoApp/Program.cs")
if program.find("builder.Configuration.AddEnvironmentVariables()") < program.find("builder.Environment.IsEnvironment(\"Docker\")"):
    fail("Program.cs: environment variables must be loaded after Docker appsettings")
for needle, why in [
    ("PersistKeysToStackExchangeRedis", "Redis-backed Data Protection"),
    ("UseForwardedHeaders", "forwarded header middleware"),
    ("MapHealthChecks(\"/health/live\"", "liveness health endpoint"),
    ("MapHealthChecks(\"/health/ready\"", "readiness health endpoint"),
    ("Database:RunMigrationsAtStartup", "migration startup guard"),
]:
    if needle not in program:
        fail(f"Program.cs: missing {why}")

require_contains(
    "BlazorAutoApp/BlazorAutoApp.csproj",
    "Microsoft.AspNetCore.DataProtection.StackExchangeRedis",
    "Redis Data Protection package",
)


test_factory = read("BlazorAutoApp.Test/TestingSetup/WebAppFactory.cs")
if "postgres:latest" in test_factory:
    fail("WebAppFactory.cs: test PostgreSQL image must be pinned")
if 'Redis__Configuration", "localhost:6379"' in test_factory:
    fail("WebAppFactory.cs: tests must not require a host Redis instance")
require_contains(
    "BlazorAutoApp.Test/TestingSetup/WebAppFactory.cs",
    'Redis__Configuration", "CHANGE_ME"',
    "test Redis disablement",
)


ci = read(".github/workflows/ci.yml")
for needle, why in [
    ("name: CI", "single CI workflow name"),
    ("pull_request:", "PR validation trigger"),
    ("python Deployment/scripts/audit_deployment.py", "deployment audit step"),
    ("dotnet restore", "restore step"),
    ("dotnet build --configuration Release --no-restore", "Release build step"),
    ("dotnet test --configuration Release --no-build", "test step"),
    ("dotnet ef migrations bundle", "migration bundle build"),
    ("docker build", "Docker image build"),
    ("if: github.event_name != 'pull_request'", "no PR artifact/image push guard"),
    ("docker push ghcr.io/grumlebob/ship:${{ github.sha }}", "immutable image push"),
]:
    if needle not in ci:
        fail(f".github/workflows/ci.yml: missing {why}")

auto_merge = read(".github/workflows/auto-merge-dependabot.yml")
for needle, why in [
    ("workflow_run:", "CI-gated Dependabot trigger"),
    ("workflows: [\"CI\"]", "CI workflow dependency"),
    ("github.event.workflow_run.conclusion == 'success'", "success-only merge guard"),
    ("github.event.workflow_run.actor.login == 'dependabot[bot]'", "Dependabot actor guard"),
    ("GH_REPO: ${{ github.repository }}", "GitHub CLI repo context"),
]:
    if needle not in auto_merge:
        fail(f".github/workflows/auto-merge-dependabot.yml: missing {why}")
if "pull_request:" in auto_merge:
    fail("Dependabot auto-merge must not trigger directly on pull_request")

deploy_lan = read(".github/workflows/deploy-lan.yml")
for needle, why in [
    ("runs-on: [self-hosted, linux, x64, homelab]", "self-hosted LAN runner targeting"),
    ("ref: ${{ inputs.image_tag }}", "checkout same commit as image"),
    ("dotnet restore", "restore before migration bundle"),
    ("bash Deployment/scripts/install-ansible.sh", "pinned Ansible installer"),
    ("bash Deployment/scripts/preflight.sh deploy", "deploy preflight"),
    ("${{ github.workspace }}/artifacts/migrations/ship-migrate", "absolute migration bundle path"),
    ("https://ship.jacobgrum.com/health/ready", "public readiness verification"),
]:
    if needle not in deploy_lan:
        fail(f".github/workflows/deploy-lan.yml: missing {why}")


prepare = read("Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml")
role_order = ["mint_base", "ssh_hardening", "docker", "firewall"]
positions = [prepare.find(f"- {role}") for role in role_order]
if any(pos < 0 for pos in positions) or positions != sorted(positions):
    fail("PrepareFreshLinuxMachine.yml: roles must run mint_base, ssh_hardening, docker, firewall")

mint_base = read("Deployment/ansible/roles/mint_base/tasks/main.yml")
for needle, why in [
    ("name: deploy", "deploy user creation"),
    ("NOPASSWD:ALL", "passwordless sudo for automation"),
    ("/home/deploy/.ssh/authorized_keys", "deploy authorized key installation"),
    ("path: /var/run/reboot-required", "post-upgrade reboot check"),
    ("name: ssh", "SSH service enablement"),
    ("path: \"{{ deploy_root }}\"", "deployment root creation"),
]:
    if needle not in mint_base:
        fail(f"mint_base role: missing {why}")

docker_role = read("Deployment/ansible/roles/docker/tasks/main.yml")
for needle, why in [
    ("UBUNTU_CODENAME", "Linux Mint Ubuntu base codename detection"),
    ("docker_apt_arch", "Docker architecture mapping"),
    (".get(ansible_architecture, ansible_architecture)", "safe Docker architecture fallback"),
    ("docker-compose-plugin", "Docker Compose plugin"),
    ("groups: docker", "deploy docker group membership"),
]:
    if needle not in docker_role:
        fail(f"docker role: missing {why}")

cloudflared_role = read("Deployment/ansible/roles/cloudflared/tasks/main.yml")
if ".get(ansible_architecture, ansible_architecture)" not in cloudflared_role:
    fail("cloudflared role: architecture mapping must have a safe fallback")

firewall_role = read("Deployment/ansible/roles/firewall/tasks/main.yml")
firewall_script = read("Deployment/ansible/roles/firewall/templates/ship-docker-user-firewall.sh.j2")
for needle, why in [
    ("ufw allow OpenSSH", "SSH firewall rule"),
    ("ship-docker-user-firewall.service", "Docker published-port firewall service"),
    ("DOCKER-USER", "Docker firewall chain"),
    ("--ctorigdstport {{ app_port }}", "app port Docker firewall restriction"),
    ("--ctorigdstport {{ postgres_port }}", "PostgreSQL Docker firewall restriction"),
    ("--ctorigdstport {{ redis_port }}", "Redis Docker firewall restriction"),
]:
    if needle not in firewall_role and needle not in firewall_script:
        fail(f"firewall role: missing {why}")

site = read("Deployment/ansible/playbooks/site.yml")
for needle, why in [
    ("Deploy PostgreSQL and Redis", "DB/Redis deployment phase"),
    ("Deploy Caddy and Cloudflare Tunnel", "load balancer deployment phase"),
    ("Stop app containers before migration", "migration downtime step"),
    ("Run database migrations once", "single migration phase"),
    ("Create pre-migration database backup", "pre-migration backup"),
    ("Deploy app servers", "app deployment after migration"),
]:
    if needle not in site:
        fail(f"site.yml: missing {why}")

caddy = read("Deployment/ansible/roles/caddy/templates/ship.caddy.j2")
if "health_uri /health/ready" not in caddy:
    fail("Caddy template must use readiness health check")
if "lb_policy cookie" not in caddy:
    fail("Caddy template must keep sticky sessions for Blazor Server")

app_role = read("Deployment/ansible/roles/app/tasks/main.yml")
if "http://127.0.0.1:{{ app_port }}/health/ready" not in app_role:
    fail("app role must wait for local readiness endpoint")
if "docker compose up -d --pull always" not in app_role:
    fail("app role must pull and start the requested image")

postgres_role = read("Deployment/ansible/roles/postgres/tasks/main.yml")
for script in ["backup-db.sh", "restore-db.sh"]:
    if script not in postgres_role:
        fail(f"postgres role must copy {script} to deploy_root")

preflight = read("Deployment/scripts/preflight.sh")
for needle, why in [
    ("REPLACE_WITH", "inventory placeholder detection"),
    ("ansible-inventory", "inventory parse check"),
    ("vault.yml", "vault existence check"),
    ("preflight ok", "successful preflight output"),
]:
    if needle not in preflight:
        fail(f"preflight.sh: missing {why}")

prepare_script = read("Deployment/scripts/prepare-fresh-linux-machines.sh")
for needle, why in [
    ("preflight.sh\" bootstrap", "bootstrap preflight"),
    ("PrepareFreshLinuxMachine.yml", "fresh-machine playbook call"),
    ("--ask-pass", "first SSH password prompt"),
    ("--ask-become-pass", "first sudo password prompt"),
    ("docker compose version", "post-bootstrap Docker Compose verification"),
]:
    if needle not in prepare_script:
        fail(f"prepare-fresh-linux-machines.sh: missing {why}")


plan = read("Plans/DEPLOYMENT_PLAN.md")
for needle, why in [
    ("## Manual Steps That Remain", "manual handoff section"),
    ("bash ./Deployment/scripts/preflight.sh bootstrap", "bootstrap preflight command"),
    ("bash ./Deployment/scripts/preflight.sh deploy", "deploy preflight command"),
    ("GitHub repository -> Settings -> Actions -> Runners", "self-hosted runner setup"),
    ("ANSIBLE_VAULT_PASSWORD", "runner vault secret"),
    ("docker compose up --build", "local Docker launch"),
    ("Database__RunMigrationsAtStartup=true", "local migrations explanation"),
    ("Durable file upload storage across both app nodes", "deferred durable uploads"),
]:
    if needle not in plan:
        fail(f"DEPLOYMENT_PLAN.md: missing {why}")

root_readme = read("README.md")
for needle, why in [
    ("HowToRunLocally.md", "local run guide link"),
    ("HowToDeploy.md", "deployment guide link"),
    ("Plans/DEPLOYMENT_PLAN.md", "detailed deployment plan link"),
    (".github/workflows/ci.yml", "single CI workflow reference"),
]:
    if needle not in root_readme:
        fail(f"README.md: missing {why}")

local_guide = read("HowToRunLocally.md")
for needle, why in [
    ("docker compose up --build", "local Docker launch command"),
    ("pwsh -File ./docker/create-dev-cert.ps1", "dev certificate command"),
    ("https://localhost:7186", "local app URL"),
    ("Database__RunMigrationsAtStartup=true", "local migration behavior"),
    ("BlazorAutoApp/settings.defaults.json", "settings defaults location"),
]:
    if needle not in local_guide:
        fail(f"HowToRunLocally.md: missing {why}")

deploy_guide = read("HowToDeploy.md")
for needle, why in [
    ("You should be able to follow this file without reading another deployment document first", "self-contained deployment promise"),
    ("Deployment/inventory/prod/hosts.yml", "inventory IP source of truth"),
    ("Deployment/inventory/prod/group_vars/all.yml", "shared deployment settings location"),
    ("Deployment/inventory/prod/vault.yml", "vault location"),
    ("Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml", "fresh-machine playbook location"),
    ("Deployment/ansible/playbooks/site.yml", "site playbook location"),
    ("sudo hostnamectl set-hostname", "hostname setup"),
    ("openssh-server", "first SSH installation"),
    ("ip -brief address", "LAN discovery"),
    ("Create DHCP reservations", "DHCP reservation step"),
    ("bash ./Deployment/scripts/install-ansible.sh", "Ansible installer"),
    ("ssh-keygen -t ed25519 -f ~/.ssh/ship_deploy", "deploy SSH key creation"),
    ("bash ./Deployment/scripts/preflight.sh bootstrap", "bootstrap preflight"),
    ("bash ./Deployment/scripts/prepare-fresh-linux-machines.sh", "fresh-machine wrapper"),
    ("ansible-vault create Deployment/inventory/prod/vault.yml", "vault creation"),
    ("vault_cloudflare_tunnel_token", "Cloudflare tunnel token secret"),
    ("cloudflared_version: 2026.5.0", "pinned cloudflared version"),
    (".github/workflows/ci.yml", "CI build/push workflow"),
    ("ghcr.io/grumlebob/ship:<git-sha>", "immutable GHCR image tag"),
    ("GitHub Actions self-hosted runner", "runner setup"),
    ("ANSIBLE_VAULT_PASSWORD", "runner vault password secret"),
    (".github/workflows/deploy-lan.yml", "LAN deployment workflow"),
    ("run_migrations: true", "deployment migration input"),
    ("ship.jacobgrum.com", "Cloudflare hostname"),
    ("bash ./Deployment/scripts/deploy.sh <git-sha>", "first deploy command"),
    ("curl -fsS https://ship.jacobgrum.com/health/ready", "public health verification"),
    ("backup-db.sh", "backup helper"),
    ("restore-db.sh", "restore helper"),
]:
    if needle not in deploy_guide:
        fail(f"HowToDeploy.md: missing {why}")


if failures:
    print("Deployment audit failed:")
    for failure in failures:
        print(f" - {failure}")
    sys.exit(1)

print("Deployment audit passed.")
