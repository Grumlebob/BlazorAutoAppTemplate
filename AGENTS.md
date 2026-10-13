# Agent working rules

Portable rules for people and coding agents working in this repository. Machine-specific paths, host names, IP addresses, keys and local permission preferences belong in your private agent configuration, never in tracked files.

## Plans

- Retained plans live in `Plans/` (tracked). Scratch notes go in `Plans.local/` (ignored).
- A plan-driven change is complete when it is verified on `origin/main` and applicable checks pass. Code/configuration changes require green exact-main CI; documentation-only changes use the exception below. Record the integrated commit and verification in the plan or the PR description.

## Changes and checks

- Code changes go through a pull request. The required check is `build-test-push`; merge only when it is green on the PR's exact head.
- Documentation-only changes (every changed file is ordinary `.md` or `.mdx` documentation; no source, build, workflow, deployment configuration, or other non-Markdown file) do not require local builds, format verification, tests, deployment gates, or waiting for PR/main CI. Review the complete PR diff, including both paths of renames, and run `git diff --check` before pushing. Use a PR for retained documentation changes. Add `[skip ci]` to documentation commits and the squash-merge title, then fetch and verify the integrated content on `origin/main`. A mixed PR uses the full code gate even if its last commit is documentation-only. Respect enforced GitHub protection; never weaken it or manufacture a passing check to use this exception.
- For changes that include code, configuration or other non-Markdown files, run the local gate before pushing; CI is not the first test run. The full list is in [docs/Test.md](docs/Test.md#local-gate). The short form:
  ```bash
  dotnet format BlazorAutoApp.sln --verify-no-changes
  bash Scripts/CI/validate-frontend-profiles.sh /tmp/frontend-profile-results # needs Docker
  bash Deployment/LocalCluster/Scripts/audit-deployment.sh
  ```
- Keep `dotnet build` and `dotnet test` sequential in one checkout. Never run them at the same time against the same files.
- When you change behaviour that the deployment audit (`Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py`) checks, update the audit in the same change: replace the old rule with a rule for the new behaviour, never just delete it.
- Rebuild and commit `BlazorAutoApp/wwwroot/tailwind.css` when Razor classes or `BlazorAutoApp.Client/Styles` change.
- Product requirements are in [docs/Requirements.md](docs/Requirements.md).
- Keep durable docs focused on current template behavior. Link canonical rules and commands instead of duplicating them; keep execution history in plans or PRs and use generic examples unless project-specific details explain template behavior.

## Hard stops

- Never run `docker volume prune`, `docker system prune`, or any unscoped prune on deployment hosts; never pass `--volumes` to Compose down on a node. Use the repository's scoped cleanup scripts.
- Never delete or reclaim a deployment lock automatically. Use `Deployment/Common/Scripts/release-deploy-lock.sh` after verifying the owner is gone.
- Never commit secrets, tokens, passwords, private keys, vault contents or real `.env` files.
- Never force-push `main` or rewrite history others have pulled.
- Never dispatch a deployment (`CD - Deploy LocalCluster`, `CD - Deploy LocalSingleNode`, `CD - Cloud`) without the operator's authorisation.
- Stage explicit paths. Do not use `git add -A` or `git add .` for integration commits.
- Do not stash, reset or overwrite someone else's uncommitted work.

## Worktree closeout

- Closeout is part of task completion: fetch and prune, verify `origin/main`, then remove finished task checkouts and local/remote branches. Preserve the primary checkout and `main` branch.
- Before cleanup, verify integrated or superseded content and no live task, process, lock, resource or open PR depends on it. Inspect tracked, untracked and ignored files; reconcile useful unmerged changes first. Squash merges require PR-head/content verification; ancestry or a closed PR alone is insufficient.
- Archive unique required notes/evidence outside the checkout and verify SHA-256. Do not archive whole checkouts or reproducible build output. Preserve private inputs, keys and other sessions' edits.
- Record each deleted branch's full SHA in its plan or PR. Run `git worktree remove` from another checkout; resolve refusals without force or broad recursive deletion.
- Verified routine cleanup needs no additional approval, including finished tasks from earlier sessions. Fast-forward primary `main` when clean and idle. Report each retained task worktree with its concrete owner or dependency; age alone is not proof.

## Shared deployment hosts

- LocalCluster and LocalSingleNode hosts can run several apps. Host-level services (Docker, Caddy, cloudflared, the deployment lock) are shared: change them only through the deployment scripts, and only remove resources you can prove this repository owns.
- Never hard-code a cluster value (node IPs, DNS suffix, domain, ports). Forks read them from their own `machines.yml`, inventory and settings.

## Setting up this machine as a deployment node

Only an explicit request to set up the current PC as a node triggers [LocalSingleNode AgentSetup](Deployment/LocalSingleNode/AgentSetup.md). A main-PC session discussing another node does not trigger setup. Reject Windows/WSL node bootstrap. The local agent follows that single runbook; the operator authenticates and runs its one sudo command.
