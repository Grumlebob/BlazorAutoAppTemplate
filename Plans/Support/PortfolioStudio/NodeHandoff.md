# Portfolio native-node and operator handoff

Parent: [master plan](../../PortfolioStudioImplementation.md). Packets: P8–P10 in [DeliveryPhases.md](DeliveryPhases.md). Record progress in [Progress.md](Progress.md); record actual host/address/login/provider facts in ignored `Plans.local/Portfolio/OperatorIntent.md`.

## 1. Intended machine and boundaries

The owner reports a fresh native Linux Mint PC with `gh auth login` completed and a fixed DHCP lease. The latest message uses an earlier demo label and the desired Portfolio label for that PC. Verify native `hostname`, address and intended identity before root setup. Do not assume it is the other React agent's existing demo node. Do not reuse that agent's runner/app/tunnel configuration or its deployment authorization.

The Windows main PC is the controller and development machine. Only a session on the native PC with an explicit instruction to set up that current PC triggers [AgentSetup.md](../../../Deployment/LocalSingleNode/AgentSetup.md). Windows/WSL may run controller tools, never native-node bootstrap. WSL controller support does not make WSL a deployment node.

Use the actual retained downstream runbooks after P3. If a documented script disappeared during cleanup, fix that repository regression through a PR rather than substituting manual `/etc`, Docker or provider operations.

## 2. Actor responsibilities

| Actor | Work |
| --- | --- |
| Main-PC agent | Plan/content/code, local checks, PRs/releases, protected Cloudflare setup, independent acceptance and authorized remote work through verified SSH |
| Native-node agent | First native identity/status, detected facts, node-only diagnostics, returned agent steps and install-user SSH authorization |
| Operator | Native-machine access, credentials/authentication, returned root command and any genuine identity/privilege/publication approval |
| Workflow runner | App-scoped CI and authorized LocalSingleNode deployments/maintenance through repository workflows |

Prefer the verified controller SSH connection whenever it can complete authorized work. Use a node-agent prompt only for a remaining local-access requirement. Return to the operator only when the agent cannot proceed through available access or the runbook explicitly assigns the step to the human.

## 3. First handoff — get the Portfolio checkout onto the native PC

Do this only after P0 has seeded Portfolio with its own app/image identity. Confirm the remote has the selected main commit before asking the operator to clone an empty repository. The template and Portfolio share an owner, so the inherited owner-only fork check does not prove the image/app name is safe; check the exact `portfolio` identity.

Give one short command sequence from the native PC's chosen development folder:

```bash
gh repo clone Grumlebob/Portfolio
cd Portfolio
```

If that checkout already exists, have the node agent inspect its status/remotes and sync safely; do not clone over it, reset dirty files or overwrite a local branch. No repository credentials go into the command.

Then give a filled-in version of this prompt using the private expected node/address:

```text
You are running on the native Linux Mint PC intended for Portfolio. The operator asks you to set up this current PC as the LocalSingleNode Portfolio node. Expected node identity: <EXPECTED_NODE>. Expected reserved IPv4: <EXPECTED_ADDRESS>.

Read AGENTS.md, Plans/PortfolioStudioImplementation.md and its Progress/NodeHandoff companions. Inspect native hostname/address, gh authentication, repository identity and Git status. Do not assume a demo label names the same node. On mismatch, report the actual versus expected identity privately and stop before root changes.

Follow Deployment/LocalSingleNode/AgentSetup.md exactly. Run setup-status with --node and --expected-address. Follow returned agent steps. For a human step, show human_message and command verbatim, then stop for the operator. Never run sudo yourself or ask for passwords/tokens. If CI capacity is missing, use the documented combined runner bootstrap and resume deferred customization through normal PR/checks/main evidence.

Record sanitized step/results and exact next action in Plans/Support/PortfolioStudio/Progress.md through the normal PR process when CI is available. Keep machine facts/secrets in ignored private notes. Do not dispatch deployment without recorded authorization or publish DNS/tunnels from the controller's credentials. Preserve all foreign/shared resources. Complete the install-user controller SSH handoff when requested.
```

The controller must fill placeholders before handing this to the operator. A missing expected hostname is an identity clarification, not a reason to ask the operator to design infrastructure.

## 4. Bootstrap with the existing state machine

On the verified native node:

```bash
bash Deployment/LocalSingleNode/Scripts/setup-status.sh \
  --node <EXPECTED_NODE> --expected-address <EXPECTED_ADDRESS> --json
```

These are placeholders from private facts. Do not paste this unfilled command as a ready operator instruction.

1. Compare detected native identity/address to intent. Confirm the explicit current-node setup request.
2. For returned actor `agent`, perform the returned command/task and rerun status.
3. For returned actor `human`, present `human_message` and `command` verbatim. Explain the step in one sentence and stop. The operator authenticates and executes that one root command.
4. For a fork/customization step, use the selected product identity and finish its local gate/PR/exact-head check/green-main cycle. If the node has no CI runner, follow the runbook's capacity-first path before requiring CI.
5. Stop after the same returned agent step fails twice. Preserve safe error output and step identity; fix repository failures through a PR.
6. Keep workflow run IDs after any watcher interruption. Inspect/resume that run; never dispatch a duplicate because monitoring stopped.

The bootstrap deploy account's sudo/Docker privileges and optional CI-user Docker access come from the runbook. The agent must not create sudoers rules, install another runner ad hoc or alter privileges manually. Start a fresh user/group session when the returned instructions require it.

If bootstrap happens early for CI, it can still be on the inherited React/Books baseline. Describe this honestly as prerequisite setup. Disable public exposure until the final Portfolio release passes P7. If the state machine requires an initial LAN deployment, use the actual operator authorization for that step; do not fake a completed release or bypass the state machine.

## 5. Pair persistent controller SSH once

Follow [ControllerSsh.md](../../../Deployment/LocalSingleNode/ControllerSsh.md) from the retained downstream checkout. The existing script exchanges public keys/verified native facts through authenticated repository variables. It preserves other user keys and does not grant new install-user privileges.

Controller preparation (Windows uses `python` if that is the installed command):

```powershell
python Deployment/LocalSingleNode/Scripts/controller-ssh.py prepare --repo Grumlebob/Portfolio --controller main-pc
```

If a verified Portfolio runner is online, use the dedicated authorization workflow from verified main:

```bash
gh workflow run localsinglenode-controller-ssh.yml \
  --repo Grumlebob/Portfolio --ref main -f controller=main-pc
```

Record and inspect the same run. Without a usable runner, give the native install-user agent this non-sudo command:

```bash
python3 Deployment/LocalSingleNode/Scripts/controller-ssh.py authorize \
  --repo Grumlebob/Portfolio --controller main-pc
```

Back on the controller, configure the privately selected alias:

```powershell
python Deployment/LocalSingleNode/Scripts/controller-ssh.py configure --repo Grumlebob/Portfolio --controller main-pc --alias <PRIVATE_ALIAS>
```

The live probe must verify native host/install user and pinned host key. An installed SSH server alone is insufficient. Never disable strict host checks, trust an unauthenticated key scan or delete unrelated known-host entries. Store key/alias/pairing details privately. Preserve these working trust records during cleanup.

## 6. LAN, CI and release gate

Use the actual downstream setup/doctor/collision commands and their documented actor/privilege requirements. Verify:

- Native identity/address matches the intended PC; Portfolio checkout/repository identity is correct.
- Runner is online and its labels/scope can execute Portfolio CI/CD without disturbing another repo.
- Docker API/local gate tools are usable by their assigned actors; a fresh group session is active if required.
- App/image/data/keys/ports/subnet/paths belong to Portfolio and do not collide with existing workloads.
- Shared locks and foreign resources are preserved. A stale lock is not permission to delete it.
- Current green-main Portfolio release exists; SHA/digest/profile/content revision agree.
- LAN deployment passes the actual final `PortfolioPublicV1` checks and independent main-PC browser/HTTP acceptance.
- Doctor/backup requirements match retained services. First deployment honestly records no previous compatible release yet.

After P7.3 implements the final acceptance profile, use the updated script with private LAN inputs:

```powershell
pwsh -NoProfile -File Scripts/Test-DeployedSite.ps1 -FrontendProfile React -AcceptanceProfile PortfolioPublicV1 -Address <DETECTED_ADDRESS> -Port <VERIFIED_HTTP_PORT>
```

Do not run that profile before the packet creates it. Record actual final profile name if implementation chooses another name. Never treat the inherited sample-Books check as final Portfolio acceptance.

## 7. Public Cloudflare launch

Follow [PublicSetup.md](../../../Deployment/LocalSingleNode/PublicSetup.md) after LAN and release readiness. The intended public URL is specified in the master plan; actual zone/account/tunnel/origin inputs and ownership IDs stay private.

The controller creates/checks owned resources using retained Common public-setup scripts, configures repository variables/connector secret, then dispatches only authorized `CD - Deploy LocalSingleNode` from verified main. Protected Cloudflare authentication belongs in the runbook's credential file/flow, never chat or tracked notes.

Give the operator only the authentication action that is actually missing. The agent handles tunnel/DNS/configuration when available tools and authorization permit it. Do not ask the owner to manually construct a tunnel or debug script internals.

After the final profile exists:

```powershell
pwsh -NoProfile -File Scripts/Test-DeployedSite.ps1 -FrontendProfile React -AcceptanceProfile PortfolioPublicV1 -BaseUrl https://portfolio.jacobgrum.com
```

Verify normal TLS, deep links, source assets/navigation data, actual Studio content and browser interactions. Check owned connector/Caddy health and unrelated workloads where present. DNS success alone is not public launch evidence.

## 8. Required format when returning to the owner

Return a concise handoff with one current action:

```text
Blocked: <specific step and missing access/input>.
On the Portfolio Linux Mint PC, run: <one exact verified command>
OR give its installed AI this prompt: <short complete prompt>
Return: <one safe result/status, not credentials>.
Then I resume: <specific packet/step>.
```

Choose command or prompt; do not send both as competing tasks unless the prompt depends on the command. If the runbook returns a human root command, present it verbatim; do not wrap several privileged actions into another script. Include the actual supplied node/address privately where it prevents ambiguity, never in public/tracked records.

Stop the dependent operation while the required answer/action is pending. Continue only independent plan/content work. On reply, verify resulting state and resume the same step. Keep bootstrap/CD IDs and private ownership/trust state so another agent can recover without repeating actions.
