# Agent working rules

Portable rules for people and coding agents working in this repository. Machine-specific paths, host names, IP addresses, keys and local permission preferences belong in your private agent configuration, never in tracked files.

## Plans

- Retained plans live in `Plans/` (tracked). Scratch notes go in `Plans.local/` (ignored).
- A plan-driven change is complete when it is merged to `main` and `main` CI is green. Record the merge commit in the plan or the PR description.

## Changes and checks

- Code changes go through a pull request. The required check is `build-test-push`; merge only when it is green on the PR's exact head.
- Documentation-only changes follow the repository owner's rule for docs. When unsure, open a PR.
- Run the local gate before pushing; CI is not the first test run. The full list is in [docs/Test.md](docs/Test.md#local-gate). The short form:
  ```bash
  dotnet format BlazorAutoApp.sln --verify-no-changes
  dotnet build BlazorAutoApp.sln --configuration Release
  dotnet test BlazorAutoApp.sln --configuration Release --no-build   # needs Docker
  bash Deployment/LocalCluster/Scripts/audit-deployment.sh
  ```
- Keep `dotnet build` and `dotnet test` sequential in one checkout. Never run them at the same time against the same files.
- When you change behaviour that the deployment audit (`Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py`) checks, update the audit in the same change: replace the old rule with a rule for the new behaviour, never just delete it.
- Rebuild and commit `BlazorAutoApp/wwwroot/tailwind.css` when Razor classes or `BlazorAutoApp.Client/Styles` change.
- Product requirements are in [docs/Requirements.md](docs/Requirements.md).

## Hard stops

- Never run `docker volume prune`, `docker system prune`, or any unscoped prune on deployment hosts; never pass `--volumes` to Compose down on a node. Use the repository's scoped cleanup scripts.
- Never delete or reclaim a deployment lock automatically. Use `Deployment/Common/Scripts/release-deploy-lock.sh` after verifying the owner is gone.
- Never commit secrets, tokens, passwords, private keys, vault contents or real `.env` files.
- Never force-push `main` or rewrite history others have pulled.
- Never dispatch a deployment (`CD - Deploy LocalCluster`, `CD - Deploy LocalSingleNode`, `CD - Cloud`) without the operator's authorisation.
- Stage explicit paths. Do not use `git add -A` or `git add .` for integration commits.
- Do not stash, reset or overwrite someone else's uncommitted work.

## Shared deployment hosts

- LocalCluster and LocalSingleNode hosts can run several apps. Host-level services (Docker, Caddy, cloudflared, the deployment lock) are shared: change them only through the deployment scripts, and only remove resources you can prove this repository owns.
- Never hard-code a cluster value (node IPs, DNS suffix, domain, ports). Forks read them from their own `machines.yml`, inventory and settings.

## Setting up this machine as a deployment node

Only an explicit request to set up the current PC as a node triggers [LocalSingleNode AgentSetup](Deployment/LocalSingleNode/AgentSetup.md). A main-PC session discussing another node does not trigger setup. Reject Windows/WSL node bootstrap. The local agent follows that single runbook; the operator authenticates and runs its one sudo command.
