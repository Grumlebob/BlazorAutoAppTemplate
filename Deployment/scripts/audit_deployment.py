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
    suffixes = {".md", ".yml", ".yaml", ".j2", ".sh", ".py", ".json", ".cs", ".csproj"}
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
    ".env.example",
    "README.md",
    "HowToRunLocally.md",
    "HowToDeploy.md",
    ".gitignore",
    "Deployment/.deploy.local.env.example",
    "Deployment/machines.example.yml",
    "Deployment/inventory/prod/hosts.yml",
    "Deployment/inventory/prod/group_vars/all.yml",
    "Deployment/inventory/prod/group_vars/node_db.yml",
    "Deployment/inventory/prod/vault.example.yml",
    "Deployment/inventory/prod/host_vars/node-db.yml",
    "Deployment/inventory/prod/host_vars/node-app1.yml",
    "Deployment/inventory/prod/host_vars/node-app2.yml",
    "Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml",
    "Deployment/ansible/playbooks/node-db.yml",
    "Deployment/ansible/playbooks/site.yml",
    "Deployment/ansible/ansible.cfg",
    "Deployment/ansible/roles/mint_base/tasks/main.yml",
    "Deployment/ansible/roles/docker/tasks/main.yml",
    "Deployment/ansible/roles/firewall/tasks/main.yml",
    "Deployment/ansible/roles/cloudflared/tasks/main.yml",
    "Deployment/ansible/roles/caddy/templates/ship.caddy.j2",
    "Deployment/ansible/roles/app/tasks/main.yml",
    "Deployment/ansible/roles/postgres/templates/node-db.env.j2",
    "Deployment/compose/app-server/docker-compose.yml",
    "Deployment/compose/node-db/docker-compose.yml",
    "Deployment/scripts/install-ansible.sh",
    "Deployment/scripts/preflight.sh",
    "Deployment/scripts/discover-machines.sh",
    "Deployment/scripts/generate-inventory.py",
    "Deployment/scripts/generate-inventory.sh",
    "Deployment/scripts/status.sh",
    "Deployment/scripts/ping-fresh-machines.sh",
    "Deployment/scripts/create-vault.sh",
    "Deployment/scripts/check-vault.sh",
    "Deployment/scripts/prepare-fresh-linux-machines.sh",
    "Deployment/scripts/deploy.sh",
    "Deployment/scripts/backup-db.sh",
    "Deployment/scripts/restore-db.sh",
    "Deployment/scripts/discover-node.sh",
    "Deployment/scripts/health-check.sh",
    "docker/setup-local.ps1",
    "docker/local-status.py",
    "docker/create-dev-cert.ps1",
    "docker-compose.yml",
    "BlazorAutoApp/Program.cs",
    "BlazorAutoApp/BlazorAutoApp.csproj",
    "BlazorAutoApp.Test/TestingSetup/WebAppFactory.cs",
]
for file in required_files:
    require_file(file)


if exists(".github/workflows/BuildAndTest.yml"):
    fail("legacy duplicate CI workflow still exists: .github/workflows/BuildAndTest.yml")

if exists("Plans/DEPLOYMENT_PLAN.md"):
    fail("duplicate deployment guide still exists: Plans/DEPLOYMENT_PLAN.md")

for stale_file in [
    "Plans/RecommendedProductionIndustryReady.md",
    "TypicalWorkflow.txt",
    "requirements.txt",
    "secrets.env",
]:
    if exists(stale_file):
        fail(f"stale root planning/local file still exists: {stale_file}")

if exists("Deployment/machines.yml"):
    fail("local machine inventory should not be committed: Deployment/machines.yml")

if exists("Deployment/.deploy.local.env"):
    fail("local deployment env should not be committed: Deployment/.deploy.local.env")

if exists("Deployment/inventory/prod/bootstrap-hosts.yml"):
    fail("bootstrap inventory should not be committed: Deployment/inventory/prod/bootstrap-hosts.yml")

removed_thin_docs = [
    "Plans/DEPLOYMENT_PLAN.md",
    "Plans/RecommendedProductionIndustryReady.md",
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
    "Plans/DEPLOYMENT_PLAN.md",
    "DEPLOYMENT_PLAN.md",
    "Plans/RecommendedProductionIndustryReady.md",
    "RecommendedProductionIndustryReady.md",
    "TypicalWorkflow.txt",
    "requirements.txt",
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
    if rel == "Deployment/scripts/audit_deployment.py":
        continue
    if "improveddb" in text or "/opt/improveddb" in text:
        fail(f"{rel}: stale improveddb reference")
    if "node-db-redis" in text or "NODE_DB_REDIS" in text:
        fail(f"{rel}: stale node-db-redis reference")
    if "db_redis" in text or "db-redis" in text:
        fail(f"{rel}: stale db_redis/db-redis reference; use node_db or node-db")
    if "releases/latest" in text:
        fail(f"{rel}: unpinned GitHub release URL")
    if "sudo apt install -y ansible" in text or "sudo apt-get install -y ansible" in text:
        fail(f"{rel}: installs distro Ansible instead of Deployment/scripts/install-ansible.sh")
    if "cd Deployment/" in text:
        fail(f"{rel}: relative cd Deployment/... command; use <repo-root>/Deployment/...")
    if "BuildAndTest" in text:
        fail(f"{rel}: stale BuildAndTest workflow reference")
    for stale_app_node in ["node-app-01", "node-app-02", "NODE_APP_01", "NODE_APP_02"]:
        if stale_app_node in text:
            fail(f"{rel}: stale app node name: {stale_app_node}")
    for removed_doc in removed_doc_references:
        if removed_doc in text:
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
if "./.env" not in local_compose:
    fail("docker-compose.yml: local compose must read .env")
if "./secrets.env" in local_compose:
    fail("docker-compose.yml: local compose must not use legacy secrets.env")
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
    ("ANSIBLE_VAULT_PASSWORD_FILE: /tmp/ship_ansible_vault_password", "vault password file for preflight"),
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
    ("check-vault.sh", "deploy vault content check"),
    ("preflight ok", "successful preflight output"),
]:
    if needle not in preflight:
        fail(f"preflight.sh: missing {why}")

prepare_script = read("Deployment/scripts/prepare-fresh-linux-machines.sh")
for needle, why in [
    ("Deployment/.deploy.local.env", "local env defaults"),
    ("LINUX_MINT_INSTALL_USER", "install user env default"),
    ("read -r -p \"Linux Mint install username:", "interactive install user prompt"),
    ("preflight.sh\" bootstrap", "bootstrap preflight"),
    ("PrepareFreshLinuxMachine.yml", "fresh-machine playbook call"),
    ("--ask-pass", "first SSH password prompt"),
    ("--ask-become-pass", "first sudo password prompt"),
    ("docker compose version", "post-bootstrap Docker Compose verification"),
]:
    if needle not in prepare_script:
        fail(f"prepare-fresh-linux-machines.sh: missing {why}")

generate_inventory = read("Deployment/scripts/generate-inventory.py")
for needle, why in [
    ("Deployment/machines.yml", "machines source file"),
    ("Deployment/inventory/prod/hosts.yml", "inventory output"),
    ("Deployment/inventory/prod/bootstrap-hosts.yml", "bootstrap inventory output"),
    ("render_bootstrap_hosts", "bootstrap inventory rendering"),
    ("node-main", "required node validation"),
    ("node-app1", "node-app1 validation"),
    ("node-app2", "node-app2 validation"),
    ("install_user", "install user field"),
]:
    if needle not in generate_inventory:
        fail(f"generate-inventory.py: missing {why}")

status_script = read("Deployment/scripts/status.sh")
for needle, why in [
    ("MODE=\"${1:-bootstrap}\"", "default bootstrap mode"),
    ("usage: $0 [bootstrap|deploy]", "phase-aware usage"),
    ("Deployment/.deploy.local.env", "local env status"),
    ("Deployment/machines.yml", "machines file status"),
    ("bootstrap inventory", "bootstrap inventory status"),
    ("REPLACE_WITH", "inventory placeholder status"),
    ("cloudflared_version", "cloudflared pin status"),
    ("check-vault.sh", "deploy vault validation status"),
    ("$MODE status ok", "successful status output"),
]:
    if needle not in status_script:
        fail(f"status.sh: missing {why}")

ping_fresh = read("Deployment/scripts/ping-fresh-machines.sh")
for needle, why in [
    ("LINUX_MINT_INSTALL_USER", "install user env default"),
    ("Linux Mint install username:", "interactive install user prompt"),
    ("bootstrap-hosts.yml", "bootstrap inventory support"),
    ("--ask-pass", "first SSH password prompt"),
    ("--ask-become-pass", "first sudo password prompt"),
]:
    if needle not in ping_fresh:
        fail(f"ping-fresh-machines.sh: missing {why}")

create_vault = read("Deployment/scripts/create-vault.sh")
for needle, why in [
    ("vault.example.yml", "vault template input"),
    ("ansible-vault encrypt", "vault encryption"),
    ("ansible-vault edit", "immediate vault edit"),
    ("check-vault.sh", "vault validation"),
    ("vault already exists", "existing vault guard"),
]:
    if needle not in create_vault:
        fail(f"create-vault.sh: missing {why}")

check_vault = read("Deployment/scripts/check-vault.sh")
for needle, why in [
    ("ansible-vault view", "vault decrypt validation"),
    ("REPLACE_WITH", "placeholder rejection"),
    ("vault_cloudflare_tunnel_token", "Cloudflare token key validation"),
    ("vault_ghcr_token", "GHCR token key validation"),
    ("$ANSIBLE_VAULT", "encrypted-file validation"),
]:
    if needle not in check_vault:
        fail(f"check-vault.sh: missing {why}")

discover_machines = read("Deployment/scripts/discover-machines.sh")
for needle, why in [
    ("whoami", "username discovery"),
    ("hostname", "hostname discovery"),
    ("ip route get 1.1.1.1", "default route discovery"),
    ("/sys/class/net/$DEFAULT_IFACE/address", "MAC discovery"),
]:
    if needle not in discover_machines:
        fail(f"discover-machines.sh: missing {why}")

gitignore = read(".gitignore")
for needle, why in [
    ("/Deployment/.deploy.local.env", "local env ignore"),
    ("/Deployment/machines.yml", "local machines ignore"),
]:
    if needle not in gitignore:
        fail(f".gitignore: missing {why}")


root_readme = read("README.md")
for needle, why in [
    ("HowToRunLocally.md", "local run guide link"),
    ("HowToDeploy.md", "deployment guide link"),
    (".github/workflows/ci.yml", "single CI workflow reference"),
]:
    if needle not in root_readme:
        fail(f"README.md: missing {why}")

local_guide = read("HowToRunLocally.md")
for needle, why in [
    (".env.example", "local env example"),
    (".env", "local env file"),
    ("pwsh -File ./docker/setup-local.ps1", "local setup helper"),
    ("python ./docker/local-status.py", "local status helper"),
    ("docker compose up --build", "local Docker launch command"),
    ("pwsh -File ./docker/create-dev-cert.ps1", "dev certificate command"),
    ("https://localhost:7186", "local app URL"),
    ("Database__RunMigrationsAtStartup=true", "local migration behavior"),
    ("BlazorAutoApp/settings.defaults.json", "settings defaults location"),
]:
    if needle not in local_guide:
        fail(f"HowToRunLocally.md: missing {why}")

env_example = read(".env.example")
for needle, why in [
    ("POSTGRES_USER=postgres", "PostgreSQL user"),
    ("Database__Host=postgres", "app DB host"),
    ("Redis__Configuration=redis:6379", "Redis configuration"),
    ("Storage__HullImages__RootPath=/app/Storage/HullImages", "local storage root"),
    ("Authentication__Google__ClientId=", "optional Google client id"),
    ("SENDGRID_API_KEY=", "optional SendGrid key"),
    ("ACCEPT_EULA=Y", "Seq EULA"),
]:
    if needle not in env_example:
        fail(f".env.example: missing {why}")

local_status = read("docker/local-status.py")
for needle, why in [
    (".env.example", "env example check"),
    (".env missing", "missing env guidance"),
    ("docker compose config", "compose validation"),
    ("HTTPS dev certificate", "certificate validation"),
    ("REQUIRED_KEYS", "required env key validation"),
]:
    if needle not in local_status:
        fail(f"docker/local-status.py: missing {why}")

setup_local = read("docker/setup-local.ps1")
for needle, why in [
    (".env.example", "env example copy"),
    ("create-dev-cert.ps1", "dev certificate setup"),
    ("local-status.py", "status check"),
]:
    if needle not in setup_local:
        fail(f"docker/setup-local.ps1: missing {why}")

deploy_guide = read("HowToDeploy.md")
for needle, why in [
    ("Follow it from top to bottom for the first deployment.", "self-contained deployment promise"),
    ("Cloudflare Tunnel is the only public ingress path", "public ingress decision"),
    ("node-main` is the ingress/control node, not an app backend by default", "node-main role boundary"),
    ("deployment/control responsibilities", "node-main control responsibilities"),
    ("third app backend (`app3`)", "optional app3 guidance"),
    ("Deployment/machines.yml", "machine source file"),
    ("Deployment/machines.example.yml", "machine source template"),
    ("bootstrap-hosts.yml", "bootstrap inventory documentation"),
    ("Deployment/.deploy.local.env", "local deployment env"),
    ("## First Deployment Checklist", "first deployment checklist"),
    ("REPLACE_WITH_NODE_MAIN_LAN_IP", "obvious machine placeholder"),
    ("node-app1", "node-app1 hostname"),
    ("node-app2", "node-app2 hostname"),
    ("bash ./Deployment/scripts/generate-inventory.sh", "inventory generation command"),
    ("bash ./Deployment/scripts/status.sh bootstrap", "bootstrap status command"),
    ("bash ./Deployment/scripts/status.sh deploy", "deploy status command"),
    ("Deployment/inventory/prod/hosts.yml", "inventory IP source of truth"),
    ("Deployment/inventory/prod/group_vars/all.yml", "shared deployment settings location"),
    ("Deployment/inventory/prod/vault.yml", "vault location"),
    ("Deployment/compose/node-db/docker-compose.yml", "DB/Redis compose location"),
    ("Deployment/compose/app-server/docker-compose.yml", "app compose location"),
    ("Deployment/ansible/roles/caddy/templates/ship.caddy.j2", "Caddy template location"),
    ("Deployment/ansible/playbooks/PrepareFreshLinuxMachine.yml", "fresh-machine playbook location"),
    ("Deployment/ansible/playbooks/site.yml", "site playbook location"),
    ("sudo hostnamectl set-hostname", "hostname setup"),
    ("openssh-server", "first SSH installation"),
    ("ip -brief address", "LAN discovery"),
    ("Create DHCP reservations", "DHCP reservation step"),
    ("bash ./Deployment/scripts/install-ansible.sh", "Ansible installer"),
    ("bash ./Deployment/scripts/ping-fresh-machines.sh", "fresh-node Ansible ping helper"),
    ("ssh-keygen -t ed25519 -f ~/.ssh/ship_deploy", "deploy SSH key creation"),
    ("bash ./Deployment/scripts/preflight.sh bootstrap", "bootstrap preflight"),
    ("bash ./Deployment/scripts/prepare-fresh-linux-machines.sh", "fresh-machine wrapper"),
    ("/opt/ship", "deploy root explanation"),
    ("bash ./Deployment/scripts/create-vault.sh", "vault creation"),
    ("bash ./Deployment/scripts/check-vault.sh", "vault validation"),
    ("git add Deployment/inventory/prod/vault.yml", "encrypted vault commit instruction"),
    ("vault_cloudflare_tunnel_token", "Cloudflare tunnel token secret"),
    ("cloudflared_version: 2026.5.0", "pinned cloudflared version"),
    ("caddy validate --config /etc/caddy/Caddyfile", "Caddy validation"),
    (".github/workflows/ci.yml", "CI build/push workflow"),
    ("ghcr.io/grumlebob/ship:<git-sha>", "immutable GHCR image tag"),
    ("Production deploys should use the Git SHA tag, not `latest`.", "immutable image guidance"),
    ("The production deployment order is:", "migration order"),
    ("## Advanced: Direct Ansible Commands", "advanced raw Ansible section"),
    ("GitHub Actions self-hosted runner", "runner setup"),
    ("ANSIBLE_VAULT_PASSWORD", "runner vault password secret"),
    (".github/workflows/deploy-lan.yml", "LAN deployment workflow"),
    ("run_migrations: true", "deployment migration input"),
    ("ship.jacobgrum.com", "Cloudflare hostname"),
    ("bash ./Deployment/scripts/deploy.sh <git-sha>", "first deploy command"),
    ("curl -fsS https://ship.jacobgrum.com/health/ready", "public health verification"),
    ("backup-db.sh", "backup helper"),
    ("restore-db.sh", "restore helper"),
    ("## Security Checklist", "security checklist"),
    ("## Deferred Work", "deferred work section"),
]:
    if needle not in deploy_guide:
        fail(f"HowToDeploy.md: missing {why}")


if failures:
    print("Deployment audit failed:")
    for failure in failures:
        print(f" - {failure}")
    sys.exit(1)

print("Deployment audit passed.")
