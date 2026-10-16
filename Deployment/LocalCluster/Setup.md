# LocalCluster setup

Use this guide to create a fresh four-node LocalCluster. Follow phases in order. For prepared nodes, use [Fork Onto An Existing LocalCluster](ForkExistingCluster.md). Choose values in [LocalCluster settings](Settings.md) before generating inventory.

Compare every SSH host fingerprint through [SSH host trust](../Common/SshTrust.md) before accepting its key. Use [the shared release contract](../Common/ReleaseContract.md) for image, CI attempt, digest, and migration artifact rules.

## 0. Install Linux Mint

**Run on:** each physical node.

Install Linux Mint, create a normal user, and disable suspend. Use this install user for bootstrap SSH.

**Checkpoint:** all four nodes have Linux Mint, a recorded install username, and no automatic suspend.

## 1. Set up the control machine

**Run on:** control machine. Linux or WSL is supported.

Install Git and GitHub CLI, authenticate, then clone the repository or fork:

```bash
sudo apt update
sudo apt install -y git gh
gh auth status || gh auth login
export LOCALCLUSTER_REPO=<github-owner>/<repo-name>
gh repo clone "$LOCALCLUSTER_REPO"
cd "$(basename "$LOCALCLUSTER_REPO")"
gh repo view --json nameWithOwner,url,defaultBranchRef --jq '"repo=\(.nameWithOwner) url=\(.url) default_branch=\(.defaultBranchRef.name)"'
```

For an existing checkout, open a terminal at its root and run the identity command. Confirm it names the intended repository.

**Checkpoint:** pwd is the repository root; GitHub CLI identifies the intended repository and main branch.

## 2. Confirm Shared Release And LocalCluster Settings

**Run on:** control machine.

Use [Settings.md](Settings.md) to choose all.yml, shared release, and GitHub values. Validate settings before setup:

```bash
bash ./Deployment/Common/Scripts/validate-common-release.sh
bash ./Deployment/LocalCluster/Scripts/validate-deploy-settings.sh
```

Replace every REPLACE_WITH value before continuing.

**Checkpoint:** both validators pass; settings identify this target.

### Deployment identity checkpoint

Confirm that repository identity and app settings belong to this target:

```bash
gh repo view --json nameWithOwner,url
bash ./Deployment/LocalCluster/Scripts/read-deploy-setting.sh app_name
bash ./Deployment/Common/Scripts/read-release-setting.sh app_image
bash ./Deployment/LocalCluster/Scripts/read-deploy-setting.sh public_hostname
```

## 3. Create Local Files And Bootstrap First SSH

**Run on:** control machine.

Create the app's deploy key and ignored machine source file:

```bash
bash ./Deployment/LocalCluster/Scripts/setup-control-machine.sh
if [ ! -f Deployment/LocalCluster/machines.yml ]; then
  cp Deployment/LocalCluster/machines.example.yml Deployment/LocalCluster/machines.yml
fi
realpath Deployment/LocalCluster/machines.yml
```

Record each node's install user, reserved IP, and MAC address in machines.yml. Do not hand-copy addresses into generated files.

**Checkpoint:** ~/.ssh/<app_name>_deploy exists; machines.yml contains one entry for each node.

### Bootstrap each node

**Run on:** each node, then control machine.

On each node, create a checkout of the same repository and run:

```bash
sudo apt update
sudo apt install -y git gh
gh auth status || gh auth login
export LOCALCLUSTER_REPO=<github-owner>/<repo-name>
gh repo clone "$LOCALCLUSTER_REPO"
cd "$(basename "$LOCALCLUSTER_REPO")"
bash ./Deployment/LocalCluster/Scripts/bootstrap-node.sh <node-name>
```

For a private fork, copy only bootstrap-node.sh and discover-machines.sh to the node if GitHub CLI login is not wanted there. Record printed username, lan_ip, and lan_mac in the matching machines.yml entry. The printed hostname confirms the selected node name.

If output is lost, rerun read-only discover-machines.sh on that node. Run bootstrap-node.sh on all four nodes before proceeding.

**Checkpoint:** each node reports username, hostname, LAN IP, and MAC; all four machines.yml entries have real values.

## 4. Reserve LAN IPs

**Run on:** router, then each node.

Reserve each ip/mac pair from machines.yml in the router. Reboot each node and confirm its active address:

```bash
ip -brief address
```

Ensure all four nodes are using their reserved IPs before proceeding.

**Checkpoint:** active addresses match machines.yml.

## 5. Generate Inventory

**Run on:** control machine.

Validate the local machine file and deployment settings, then generate inventory:

```bash
bash ./Deployment/LocalCluster/Scripts/validate-machines.sh
bash ./Deployment/LocalCluster/Scripts/generate-inventory.sh
bash ./Deployment/LocalCluster/Scripts/summary.sh
```

validate-machines.sh checks required nodes, placeholders, unique addresses and MACs, usernames, and settings. Success: prints OK lines for machines.yml, deployment settings, and all four nodes. generate-inventory.sh writes hosts.yml and bootstrap-hosts.yml from machines.yml. Normal deploy uses hosts.yml; bootstrap inventory is only for fresh nodes. summary.sh prints the selected repository, hostname, ports, runner labels, and node addresses.

Commit Deployment/Common/release.yml, Deployment/LocalCluster/inventory/prod/group_vars/all.yml, and generated Deployment/LocalCluster/inventory/prod/hosts.yml. Keep machines.yml and bootstrap-hosts.yml local and ignored.

```bash
git add Deployment/Common/release.yml
git add Deployment/LocalCluster/inventory/prod/group_vars/all.yml
git add Deployment/LocalCluster/inventory/prod/hosts.yml
git commit -m "Configure production deployment settings"
```

**Checkpoint:** validation succeeds for all four nodes; generated inventory uses reserved IPs; summary identifies this target; release, settings, and hosts.yml are committed.

## 6. Verify Bootstrap Access

**Run on:** control machine with a full repository checkout.

Run this only from a full repository checkout on the control machine. Check the script exists, then verify bootstrap SSH:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
test -f "$REPO_ROOT/Deployment/LocalCluster/Scripts/verify-bootstrap.sh"
bash "$REPO_ROOT/Deployment/LocalCluster/Scripts/verify-bootstrap.sh"
```

This checks bootstrap status, preflight, and Ansible ping through bootstrap-hosts.yml. If ping fails, compare the SSH host fingerprint using [SSH host trust](../Common/SshTrust.md), then test SSH to the failing node.

**Checkpoint:** all four nodes return pong; output includes bootstrap verification ok.

## 7. Prepare Fresh Linux Machines

**Run on:** control machine.

```bash
bash ./Deployment/LocalCluster/Scripts/prepare-fresh-linux-machines.sh
```

The script creates the deploy user, installs key-based SSH, hardens SSH, installs Docker, configures host and published-port firewalls, and creates runtime directories.

**Checkpoint:** every node responds to Ansible, Docker, and Docker Compose checks. Later deployment uses the deploy user and ~/.ssh/<app_name>_deploy.

## 8. Create The Cloudflare Tunnel

**Run on:** Cloudflare dashboard and control machine.

Create a remotely managed Cloudflare Tunnel. Use the exact cloudflare_tunnel_name from all.yml. Do not run Cloudflare's connector install command; Ansible installs the connector later. Copy only its tunnel token into the encrypted vault.

Add configured public_hostname with service type HTTP and URL 127.0.0.1:80. Cloudflared connects to Caddy on node-main; do not enter an app-node address or expose database, Redis, or observability ports. Side-by-side apps use the same tunnel and add separate hostnames.

**Checkpoint:** tunnel and public hostname exist; token is ready for vault setup.

## 9. Create Secrets And The GitHub Vault Secret

**Run on:** control machine.

```bash
bash ./Deployment/LocalCluster/Scripts/setup-secrets.sh
bash ./Deployment/LocalCluster/Scripts/check-vault.sh
```

Enter requested vault values and save the vault password in a password manager. The script creates one encrypted per-app Data Protection certificate and passphrase when either is absent; it preserves a complete existing pair. Do not rotate this pair during routine deployments. The certificate lets app replicas unwrap keys stored in PostgreSQL, so database recovery also needs this vault. The script can set GitHub secret ANSIBLE_VAULT_PASSWORD when GitHub CLI is authenticated. If it cannot, add that secret through GitHub repository settings. Commit only encrypted Deployment/LocalCluster/inventory/prod/vault.yml; never commit plaintext secrets.

**Checkpoint:** check-vault.sh reports that the encrypted vault decrypts and contains required non-placeholder keys.

## 10. Install The GitHub Actions Runner

**Run on:** control machine; runner is installed on node-main.

For a new fork without an inherited runner, run this after node preparation and before the first PR or main CI run:

```bash
bash ./Deployment/LocalCluster/Scripts/install-github-runner.sh
bash ./Deployment/LocalCluster/Scripts/check-github-runner.sh
RUNNER_LABEL="$(bash ./Deployment/LocalCluster/Scripts/read-deploy-setting.sh runner_label)"
gh variable set LOCALCLUSTER_RUNNER_LABEL --body "$RUNNER_LABEL"
gh variable set CI_RUNNER_LABEL --body "$RUNNER_LABEL"
gh variable set CI_RUNNER_HOST --body node-main
```

Confirm the runner is online in repository Actions settings. CI_RUNNER_HOST must match the runner host. See [GitHub variables and secrets](Settings.md#github-variables-and-secrets). Keep external pull request code off self-hosted runners.

**Checkpoint:** runner is online; LOCALCLUSTER_RUNNER_LABEL, CI_RUNNER_LABEL, and CI_RUNNER_HOST are set before the first PR.

## 11. Build And Push The First Image

**Run on:** GitHub.

Enable GitHub Actions and grant package write permission. For a new fork without an inherited runner, complete phase 10 and set runner variables before opening the first PR. Require build-test-push on the exact PR head, then merge. Main CI publishes the image and migration artifact. See [the shared release contract](../Common/ReleaseContract.md).

Optional sanity check: before deploying, confirm the image tag exists.

```bash
APP_IMAGE="$(bash ./Deployment/Common/Scripts/read-release-setting.sh app_image)"
APP_VERSION="$(git rev-parse HEAD)"
docker manifest inspect "${APP_IMAGE}:${APP_VERSION}" >/dev/null
```

**Checkpoint:** main CI passes and publishes the release for the merged commit.

## 12. Configure The GitHub CD Environment

**Run on:** GitHub repository settings.

New environment -> localcluster

Allow deployment from main:

- Deployment branches and tags: Selected branches and tags
- Allowed branch: main

For multiple maintainers, add required reviewers. GitHub variables, including optional LOCALCLUSTER_ENVIRONMENT, are in [Settings.md](Settings.md#github-variables-and-secrets).

**Checkpoint:** Environment localcluster exists and allows deployments from main.

## 13. First Deploy From GitHub Actions

**Run on:** GitHub, then control machine.

In Actions, run CD - Deploy LocalCluster from main. Use run_migrations: true for the first deployment and releases with EF migrations. Leave target_sha empty to select current main. The workflow verifies release provenance before deployment.

**Checkpoint:** CD completes and its acceptance check passes. If the migration artifact is missing or expired, use recovery in [the shared release contract](../Common/ReleaseContract.md).

## 14. Verify the deployment

**Run on:** control machine.

```bash
bash ./Deployment/LocalCluster/Scripts/acceptance-check.sh
```

**Checkpoint:** public /health/ready succeeds; app nodes, database, Redis, Caddy, and Cloudflared are healthy.

## 15. Verify LocalCluster Observability

**Run on:** control machine, after acceptance passes.

Run the telemetry check when `observability_enabled` is true:

```bash
bash ./Deployment/LocalCluster/Scripts/observability-doctor.sh
```

**Checkpoint:** observability doctor passes, or observability was deliberately disabled. Use [LocalCluster observability operations](Operations.md#observe-the-stack) for the Grafana tunnel.
