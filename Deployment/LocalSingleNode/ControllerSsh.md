# Persistent controller SSH access

LocalSingleNode setup includes a controller SSH handoff. Installing the SSH server and importing GitHub public keys on the node does not prove that the main PC has a matching private key, the correct login, or trusted host identity. Complete this handoff before calling controller access ready. It also applies to an existing node; do not bootstrap it again.

Use `Scripts/controller-ssh.py` from this directory. It requires Python 3, OpenSSH and authenticated GitHub CLI on the controller and native node. Both GitHub sessions need repository variable access. Windows and WSL are supported controllers; use the same environment for preparation and configuration. The node command runs only as the recorded original install user on native Linux, without sudo.

## Pair a controller once

Choose a unique controller name within the repository and a local SSH alias. The examples use placeholders. Keep actual repository/node/address/user/key details in private configuration, never tracked files or public reports.

1. On the controller, create its dedicated key and publish only the public key through authenticated repository variables:

   ```bash
   python3 Deployment/LocalSingleNode/Scripts/controller-ssh.py prepare --repo OWNER/REPOSITORY --controller main-pc
   ```

   On Windows, use `python` when that is the installed Python command. The private key remains under the controller user's `.ssh/localsinglenode/` with restricted permissions. The key is generated without a passphrase for unattended agent use; protect the controller user account and its storage. No password or private key goes to GitHub or the node.

2. If the existing native Actions runner is online, the controller can dispatch the dedicated authorization workflow from verified main:

   ```bash
   gh workflow run localsinglenode-controller-ssh.yml --repo OWNER/REPOSITORY --ref main -f controller=main-pc
   ```

   Record the run ID immediately and inspect that same run until it succeeds; do not dispatch again because watching stops. The workflow requires main, an enabled LocalSingleNode target and the expected native hostname. It uses the runner's existing privilege to execute only the authorization script as the original install user with that user's existing GitHub authentication. It performs no backup, cleanup, restart or deployment. Temporary public program files are removed when the step exits.

   Without a usable runner, the existing native agent can instead run this command as the original install user, without sudo:

   ```bash
   python3 Deployment/LocalSingleNode/Scripts/controller-ssh.py authorize --repo OWNER/REPOSITORY --controller main-pc
   ```

   The script checks the repository's `LOCALSINGLENODE_HOST` against the native hostname and recorded install user. It adds the controller public key to that user's `authorized_keys`, preserves existing entries and restrictions, and publishes the address, login, node Ed25519 public host key and controller public key through repository variables. Repeated authorization does not duplicate the unrestricted key. It does not change sudoers, Docker groups, firewall, SSH configuration, runners or application services.

3. Back on the controller, save and verify the alias:

   ```bash
   python3 Deployment/LocalSingleNode/Scripts/controller-ssh.py configure --repo OWNER/REPOSITORY --controller main-pc --alias demo-node
   ssh demo-node
   ```

   Configuration uses the authenticated node record instead of trusting an unauthenticated key scan. It pins host identity in a dedicated known-hosts file and adds one include to the user's existing SSH config. Existing config remains intact; conflicting aliases and changed pinned host keys stop setup. A live passwordless probe must confirm the native hostname and original install user. Batch mode, strict host checking, one selected identity, connection timeouts and keepalive are persistent. Agent forwarding is disabled.

Report only `controller key published`, `node authorization complete`, `controller alias verified` or the blocked step in public coordination. Repository variables are configuration, not secrets; never reference these values in public workflow logs. Their [API requires authenticated repository access](https://docs.github.com/en/rest/actions/variables#get-a-repository-variable). Private keys, passwords and credential files never belong in variables.

## Use and maintain access

Prefer this verified SSH connection for authorized node inspection and repository work from the main PC. SSH access does not grant approval for deployments, shared-service changes or privileged commands. Continue to use the deployment runbooks and existing operator authorization. The original install user retains its existing privileges; this handoff grants no root or Docker permissions.

Record the controller name, alias and pairing status in an ignored private note. Keep sanitized requests/results in the relevant retained plan or PR and sync before writing. Once SSH works, the controller can perform most checks directly; use the node-side agent only for a remaining local-access or operator requirement.

Remove obsolete temporary handoff files after coordination is complete. Keep reusable setup commands, runbooks and required sanitized evidence. Do not remove private keys or trust records that provide the working persistent connection.

After a LAN address change, update native machine facts through the existing node process, repeat `authorize`, then repeat `configure`. The pinned host key must remain identical. A DHCP reservation makes address changes less likely. For a replaced node or intentional host-key rotation, verify the new public key through the native session before deliberately replacing the dedicated local trust record. Never disable strict checking or delete unrelated known-host entries to bypass a mismatch.

To revoke a controller, remove only its exact unrestricted public-key entry from the install user's `authorized_keys` through an authorized native session. Remove its two repository variables and its dedicated local include/config/key files only after checking their ownership. Preserve other controllers, user keys and shared node services.

## Docker-backed readiness

When the original install user's SSH session lacks Docker access, use [the read-only native runner diagnostics](Readiness.md). The existing deployment account performs the ordinary candidate collision check, configured doctor and workload/backup/capacity inspection without sudo or application mutation. This preserves the SSH user's existing privileges and keeps candidate installation values out of public logs.
