# Rename the template to GrumPlates

Status: **complete**. Executed 2026-10-28, Phase 8 (local folder rename) included; see §11.

Rename the GitHub repository `Grumlebob/BlazorAutoAppTemplate` to `Grumlebob/GrumPlates`, rename every `BlazorAutoApp*` project, folder, namespace and identifier to `GrumPlates*`, rename the local checkout folder, and clean up what the old name leaves behind. No backward compatibility is kept: old image labels, old release payloads and old recovery markers are retired, not aliased.

Work through the phases in order. Each step says what to run and how to check it. Stop at any **STOP** condition and report instead of improvising.

## 1. Name mapping

Apply in this order (longer names first). Matching is case-sensitive.

| Old | New | Where it appears |
| --- | --- | --- |
| `BlazorAutoAppTemplate` | `GrumPlates` | Repository name, URLs, test fixtures, `release-status.py` guards, `ci_report_store.py` default |
| `blazorautoapptemplate` | `grumplates` | Lowercase repository slugs in tests |
| `BlazorAutoApp` | `GrumPlates` | Solution, projects, folders, namespaces, assembly (`GrumPlates.dll`), `App:Name` default, docs, dashboards |
| `blazorautoapp` | `grumplates` | Image labels `com.grumplates.*`, Sonar schema ids `grumplates.sonar-*/1`, Alloy compose filter, Sonar compose label |
| `blazor-auto-app` | `grumplates` | npm package `grumplates-react` |

**Do not change:**

- `BlazorAuto`, `BlazorAutoV1` and `FrontendComposition.BlazorAuto.cs`. `BlazorAuto` is the frontend-profile name for Blazor Interactive Auto, not the template name. The replacements above never match it, because it has no `App` suffix. Phase 2 checks the counts.
- The deployment identity: `app_name: books` (LocalCluster, LocalSingleNode), `bookscloud` (Cloud), `deploy_root: /opt/books`, `app_image: ghcr.io/grumlebob/books`, `migration_bundle_name: books-migrate`. These belong to the Books sample feature, not to the template name. Keeping them means the deployed volumes, databases, Caddy sites, Data Protection keys and Redis keys on the nodes do not move. On nodes, `App__Name` comes from `app_name`, so the `App:Name` default changes only local development.
- Everything under `Plans/` except this file. Plans are execution history (see `AGENTS.md`). Their old links still work through GitHub's redirect. This includes `Plans/ZeroCostDiagnosticArchiveManifest-20261017.json`; Phase 7 retires it.
- Shared host names: `/tmp/localcluster-deploy.lockdir`, CI resource labels, `localcluster-books` and `localsinglenode-books` runner labels.

## 2. Facts gathered on 2026-10-28

Re-check any fact a step depends on before acting on it.

- Scope outside `Plans/`: about 1,316 matches in 364 tracked files, and 397 tracked paths under `BlazorAutoApp/`, `BlazorAutoApp.Client/`, `BlazorAutoApp.Core/`, `BlazorAutoApp.React/` and `BlazorAutoApp.Test/`. Six files have the name in their own file name: the five `.csproj`/`.sln` files and `Scripts/Quality/tests/fixtures/sarif/BlazorAutoApp.Test.sarif`. No other nested folder has the name.
- Baseline for the guard in Phase 2: `git grep -I -o -w 'BlazorAuto' -- ':!Plans/*' | wc -l` = **265**; `git grep -I -o 'BlazorAutoV1' -- ':!Plans/*' | wc -l` = **78**.
- `Grumlebob/GrumPlates` did not exist (HTTP 404), so the name was free.
- The template checkout has two remotes, `origin` and `improveddb`, so `gh` commands need `-R <owner>/<repo>`.
- No open PRs. The branch `coord/node-inventory-handoff` (3 commits, 2026-10-11) is not part of this work. Leave it alone.
- Live deployments: LocalCluster (`books`, nodes in `Deployment/LocalCluster/inventory/prod/hosts.yml`: load balancer 192.168.0.52, app servers 192.168.0.7 and 192.168.0.59, db 192.168.0.24) and LocalSingleNode on `node-demo` (192.168.0.212): primary `books` and additional `books-react` (public at `demo.jacobgrum.com`). `node-demo` also hosts CarbonCalculator, which must not be touched. Cloud has not been deployed since 2026-06 and is out of scope.
- Runners: `node-main-books` (labels `localcluster`, `localcluster-books`) and `node-demo-books` (`localsinglenode-books`). The node-demo systemd unit is `actions.runner.grumlebob-blazorautoapptemplate.node-demo-books.service`; scripts find it by glob, so the old unit name keeps working.
- The main PC can SSH to `node-demo` as `jgrum` with `ssh -F ~/.ssh/localsinglenode/8bfb4c4094be2598.conf node-demo`. `jgrum` has **no passwordless sudo**, and `/opt/books*/` and `/home/deploy/` are unreadable to it. The main PC has no saved SSH config for the LocalCluster nodes.
- The `gh` token scopes are `delete_repo, gist, read:org, repo, user, workflow, write:packages`. They do **not** include `delete:packages`.
- GHCR packages owned by the template: `books` (100+ versions), `books-react` (100+), `private-books-release-payload` (16), `private-books-react-release-payload` (16), plus legacy public `books-release-payload` and `books-react-release-payload` (33 each, last written 2026-10-15). In the template, the legacy names appear only in test fixtures. `registry-retention.yml` always keeps the config-only bootstrap manifest `sha256:25fef0757d76c56cd980dca6cde1e156ab7a2daa902306ab48da4e12a6e7343f`. It was created 2026-10-15 and must survive.
- Local leftovers: Docker volumes `blazorautoapp_*` (8) and `blazorautoapp-codex_*` (3), Sonar volumes `sonarqube-blazorautoapptemplate-5b8fdacf-{data,database,extensions,logs}`, folder `%LOCALAPPDATA%\BlazorAutoAppQuality\SonarQube\blazorautoapptemplate-5b8fdacf`. The Sonar stack was not running.
- Not part of this work, keep: `%LOCALAPPDATA%\BlazorAutoApp\worktree-closeout` and `%LOCALAPPDATA%\BlazorAutoAppTemplate\{ProtectedState,TaskArchives}`. They hold archived evidence from earlier closeouts.
- The WSL clone is `/home/grumbo/src/BlazorAutoAppTemplate`, and the gate work dir is `~/template-gate`. `~/bin/repo-gate.sh` finds `*.sln` and `*/*.Test.csproj` by pattern, so it needs no edit.
- Downstream repos `Portfolio` and `CarbonCalculator` share history with the template but port template changes by hand rather than merging (Portfolio is 201 commits behind and last merged upstream before its own rename). The rename only changes the path mapping they port with. `ImprovedDb` keeps its `BlazorAutoApp` names and is out of scope.

## 3. Why the cutover is ordered this way

The deployed nodes record which repository owns them. After the GitHub rename, CD passes `source_repo_url=https://github.com/Grumlebob/GrumPlates`, and these checks would refuse it:

| Check | File on node | Code |
| --- | --- | --- |
| LocalCluster current release must come from this repo | `/opt/books/release.json` | `Deployment/LocalCluster/ansible/playbooks/site.yml` "Require existing release marker to belong to this repository" |
| LocalSingleNode app ownership | `/etc/localsinglenode/apps/{books,books-react}.json` | `Deployment/LocalSingleNode/Scripts/lib/collisions.py` `_check_owned_paths` |
| LocalSingleNode public tunnel ownership | `/etc/{books,books-react}/public.json` (whichever exists) | `collisions.py` `_check_caddy_sites`, `public_collisions.py` |
| Release status (registry protection input) | `release.json`, `release-state/previous.json` | `Deployment/Common/Scripts/Component/lib/release_status.py` `summarize_marker` |
| Runner identity (setup, and CI when runner routing is on) | `/opt/actions-runner-books/.runner`, `/home/deploy/actions-runner-books*/.runner` | `install-github-runner.sh`, `LocalSingleNode/Scripts/lib/runner.py`, `Scripts/CI/verify_ci_runner.py` |
| Registry retention refuses foreign payloads | GHCR image labels `org.opencontainers.image.source`, `localcluster.ci.repository` | `Deployment/Common/Scripts/Component/lib/registry_inventory.py` `_source` |

The two `release-status.py` scripts also refuse any repository except a hardcoded name.

So the order is:

1. Prepare the code PR while the repository still has the old name (PR CI does not use those hardcoded guards).
2. Pause scheduled workflows.
3. Rename the GitHub repository and merge the PR.
4. Rewrite the node markers once (operator, sudo).
5. Deploy every instance **twice**, so that both the current and the previous marker point at new-label images.
6. Delete the old-label GHCR versions, then resume the schedules.

## 4. Manual operator steps

The agent cannot do these. Each is also marked **OPERATOR** where it appears in the phases.

1. **Phase 4.7, sudo on the nodes.** Run the marker-rewrite script with `sudo` on `node-demo` and on each LocalCluster node. The agent has no sudo, and no SSH access to the LocalCluster nodes.
2. **Phase 6.1, `gh auth refresh -h github.com -s delete:packages`.** This is an interactive browser approval. It is needed to delete old GHCR versions.
3. **Phase 8.1, before the local folder rename.** Close every program that has `C:\Users\jgrum\Documents\Programming\Csharp\BlazorAutoApp` open (Visual Studio, Rider, VS Code, terminals, Claude Code and Codex sessions started there). Windows cannot rename a folder that is in use, and the agent's own session is one such process. Then start a new agent session in `C:\Users\jgrum\Documents\Programming\Csharp` to run Phase 8.

Deploys need the operator's authorisation (`AGENTS.md` hard stop). Record the authorisation in §11 before Phase 5. Without it, stop after Phase 4.6 and ask.

## Phase 0: Preflight (agent)

1. `cd /c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp && git fetch --prune origin && git status --short --branch`. **STOP** if the tree is dirty or `main` differs from `origin/main`.
2. `gh pr list -R Grumlebob/BlazorAutoAppTemplate --state open`. **STOP** if any PR is open: finish or park it first, because its branch would conflict with the rename.
3. `gh run list -R Grumlebob/BlazorAutoAppTemplate --status in_progress` and `--status queued`. Both must be empty.
4. Record the current health, so that later failures can be compared against it. Dispatch `release-status.yml` three times (`target=localcluster`; `target=localsinglenode app_instance=primary`; `target=localsinglenode app_instance=additional`), for example `gh workflow run release-status.yml -R Grumlebob/BlazorAutoAppTemplate -f target=localcluster -f app_instance=primary`. Wait for them, and record the run URLs and results in §11. **STOP** if any fails before the rename: fix that first.
5. Re-run the counts in §2 (matches, paths, `BlazorAuto` 265, `BlazorAutoV1` 78). If they changed, update §2 before continuing.
6. Confirm the Sonar stack is stopped: `docker compose ls` must not list a `sonarqube-*` project. If it does, run `pwsh -File Scripts/Quality/SonarQubeServer.ps1 -Stop`.
7. Create the working folder for scripts and lists: `mkdir -p Plans.local/GrumPlatesRename` (`Plans.local/` is ignored). Commands below use `SCRATCH=/c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp/Plans.local/GrumPlatesRename`. Shell variables do not persist between agent tool calls, so set `SCRATCH` at the start of each command that uses it.

## Phase 1: Rename on a branch (agent)

1. `git switch -c chore/rename-grumplates main`.
2. Rename the folders and files with `git mv`. This keeps history and moves ignored content (`bin/`, `obj/`, `node_modules/`, `*.csproj.user`) along with each folder:
   ```bash
   git mv BlazorAutoApp.Client GrumPlates.Client
   git mv BlazorAutoApp.Core GrumPlates.Core
   git mv BlazorAutoApp.React GrumPlates.React
   git mv BlazorAutoApp.Test GrumPlates.Test
   git mv BlazorAutoApp GrumPlates
   git mv BlazorAutoApp.sln GrumPlates.sln
   git mv GrumPlates/BlazorAutoApp.csproj GrumPlates/GrumPlates.csproj
   git mv GrumPlates.Client/BlazorAutoApp.Client.csproj GrumPlates.Client/GrumPlates.Client.csproj
   git mv GrumPlates.Core/BlazorAutoApp.Core.csproj GrumPlates.Core/GrumPlates.Core.csproj
   git mv GrumPlates.Test/BlazorAutoApp.Test.csproj GrumPlates.Test/GrumPlates.Test.csproj
   git mv Scripts/Quality/tests/fixtures/sarif/BlazorAutoApp.Test.sarif Scripts/Quality/tests/fixtures/sarif/GrumPlates.Test.sarif
   ```
   If a `git mv` of a folder fails with "Permission denied", a program has a file open (often VS or `dotnet build-server`). Run `dotnet build-server shutdown`, close the program and retry. Never use `--force`.
3. Check: `git ls-files | grep -v '^Plans/' | grep -i blazorautoapp` must print nothing. If it prints a path, `git mv` it using the mapping in §1.
4. Rename the ignored root file so that Rider keeps its settings: `[ -f BlazorAutoApp.sln.DotSettings.user ] && mv BlazorAutoApp.sln.DotSettings.user GrumPlates.sln.DotSettings.user`. Delete the IDE caches that hold the old names, because they are regenerated: `rm -rf .vs .idea`.
5. Save this script as `Plans.local/GrumPlatesRename/replace_names.py` (ignored folder) and run it from the repository root with `python3 Plans.local/GrumPlatesRename/replace_names.py`:
   ```python
   #!/usr/bin/env python3
   """Replace BlazorAutoApp names with GrumPlates in tracked text files outside Plans/."""
   import pathlib
   import subprocess

   REPLACEMENTS = [  # order matters: longer names first
       ("BlazorAutoAppTemplate", "GrumPlates"),
       ("blazorautoapptemplate", "grumplates"),
       ("BlazorAutoApp", "GrumPlates"),
       ("blazorautoapp", "grumplates"),
       ("blazor-auto-app", "grumplates"),
   ]

   listed = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout
   changed = 0
   for raw in filter(None, listed.split(b"\0")):
       path = raw.decode("utf-8")
       if path.startswith("Plans/"):
           continue
       file = pathlib.Path(path)
       if file.is_symlink() or not file.is_file():
           continue
       data = file.read_bytes()
       if b"\0" in data:
           continue  # binary
       try:
           text = data.decode("utf-8")  # a BOM survives as U+FEFF; line endings are untouched
       except UnicodeDecodeError:
           print("SKIPPED non-UTF-8 file:", path)
           continue
       new = text
       for old, replacement in REPLACEMENTS:
           new = new.replace(old, replacement)
       if new != text:
           file.write_bytes(new.encode("utf-8"))
           changed += 1
   print("changed files:", changed)
   ```
   Expect about 364 changed files. **STOP** if it prints any `SKIPPED` line: inspect that file by hand.
6. Run the guards. All of them must pass:
   ```bash
   git grep -nIiE 'blazorautoapp|blazor-auto-app' -- ':!Plans/*'          # must print nothing
   git grep -I -o -w 'BlazorAuto' -- ':!Plans/*' | wc -l                    # must be 265
   git grep -I -o 'BlazorAutoV1' -- ':!Plans/*' | wc -l                     # must be 78
   git grep -nI 'GrumPlatesTemplate\|grumplatestemplate'                    # must print nothing
   git diff --check
   ```
7. Make the hand edits that the script cannot reason about:
   1. `docs/StandaloneProduct.md`: the final search command now reads `GrumPlates|grumplates|grumplates|Books`. Change it to `git grep -nIiE "GrumPlates|Books" -- ':!Plans'`, because `-i` already covers lowercase. Check the rename table above it: rows should read `GrumPlates.sln`, `GrumPlates.React`, npm package `grumplates-react`, labels `com.grumplates.*`, Alloy filter `grumplates`.
   2. `docs/HowToForkThisRepo.md` line 31 and `README.md`: read them and fix wording that the replacement made awkward. For example, "GrumPlates is a .NET 10 application template" is correct; do not add other rewording.
   3. `Deployment/LocalCluster/Scripts/release-status.py` and `Deployment/LocalSingleNode/Scripts/release-status.py`: the guard must now read `"Grumlebob/GrumPlates"`. Change the error text "status workflow is bound to the Template repository" only if a test asserts it; otherwise leave it.
   4. `docker/observability/alloy/config.alloy`: the filter is now `regex = "grumplates"`. That matches the local Compose project once the folder is renamed in Phase 8, because Compose names the project after the folder. Do not add a `name:` key to `docker-compose.yml`.
   5. `.codex/config.toml`, `.claude/skills/setup-local-single-node/SKILL.md` and `.run/Local Docker Stack.run.xml` are tracked and were handled by the script. Open each one and check that its paths still resolve (for example `GrumPlates/GrumPlates.csproj`).
8. Rebuild the generated files and check them:
   1. Tailwind: `cd GrumPlates.Client && npm ci && npm run css:build && cd ..`, then `git diff --stat -- GrumPlates/wwwroot/tailwind.css`. A diff is acceptable only if it comes from the rename (for example a path comment). Commit whatever the build produces, because CI runs `git diff --exit-code` on it.
   2. npm locks: `cd GrumPlates.Client && npm ci && cd ../GrumPlates.React && npm ci && cd ..`. `git status --short -- '*package-lock.json'` must show only the changes from step 5 (the `name` fields). If `npm ci` rewrites a lock file, run `npm install --package-lock-only` in that folder and commit the result.
   3. React API contract: `cd GrumPlates.React && npm run api:check && cd ..`. It must pass with no change to `GrumPlates.React/api/openapi.json` (`docs/StandaloneProduct.md` says the contract does not change on a rename).
   4. EF model: run the migrations check exactly as `ci.yml` does near the `--project GrumPlates/GrumPlates.csproj --startup-project GrumPlates/GrumPlates.csproj` lines. There must be no pending model changes. Migration IDs do not change, so `__EFMigrationsHistory` on the nodes is unaffected.
9. `dotnet build GrumPlates.sln`, then (sequentially, never in parallel) `dotnet test GrumPlates.sln`. Fix failures caused by the rename only.
10. Stage the changes without `git add -A`: `git add --update` (tracked files, including renames), then `git status --short`. **STOP** if `git status --short` shows untracked files (`??`): the rename should not create new files. Investigate, and `git add -- <path>` only files that are clearly part of the rename.
11. Commit:
    ```text
    refactor: rename the template to GrumPlates

    Rename the solution, projects, folders, namespaces, assembly, npm
    package, image labels and Sonar schema ids from BlazorAutoApp to
    GrumPlates, and point repository guards at Grumlebob/GrumPlates.
    Deployment identity (books) and the BlazorAuto frontend profile are
    unchanged.

    Co-Authored-By: <attribution line from the session>
    ```

## Phase 2: Local gate (agent)

1. Run the full gate in WSL against the primary checkout, which is still at the old Windows path at this point:
   ```bash
   MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -lc 'GATE_SRC=/mnt/c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp GATE_WORK=$HOME/template-gate ~/bin/repo-gate.sh chore/rename-grumplates 2>&1 | tee /tmp/gate-rename.log | tail -3'
   ```
   The result must be `GATE RESULT: PASS for <full sha>`, and `GATE HEAD` must equal `git rev-parse HEAD`. Logs are in `~/gate-logs/<8-char sha>/<step>.log`.
2. If the gate has no step for them, also run the short-form checks from `AGENTS.md`: `dotnet format GrumPlates.sln --verify-no-changes`, `bash Scripts/CI/validate-frontend-profiles.sh /tmp/frontend-profile-results`, `bash Deployment/LocalCluster/Scripts/audit-deployment.sh`.
3. Typical failures and their fixes:
   - An audit rule in `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py` still expects an old string. The script should have renamed both sides; find the mismatch with `git grep -n '<string from the error>'`.
   - A test asserts a path such as `base / "grumlebob" / "grumplates"` (`Scripts/CI/tests/test_ci_report_store.py`). This is expected after the rename and should already pass.
   - A Sonar test compares `blazorautoapp.sonar-*/1`: it must now be `grumplates.sonar-*/1` on both sides.
4. Commit each fix as a separate commit on the branch, and re-run the gate until it passes on the final head.

## Phase 3: Pull request (agent)

1. `git push -u origin chore/rename-grumplates`.
2. Open the PR with `gh pr create -R Grumlebob/BlazorAutoAppTemplate --base main --title "refactor: rename the template to GrumPlates"`. In the body, link this plan, list the mapping table from §1 and the "do not change" list, and end with the session's PR attribution line.
3. Wait for `build-test-push` on the exact PR head. It must be green. **Do not merge yet.**
4. Review the complete diff: `gh pr diff -R Grumlebob/BlazorAutoAppTemplate <n> --name-only | wc -l` (about 760 paths: the renames count twice) and spot-read `GrumPlates/Dockerfile`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `Deployment/LocalCluster/ansible/playbooks/site.yml`, `Deployment/LocalSingleNode/ansible/roles/single_node_stack/tasks/main.yml`, `docs/StandaloneProduct.md`.

## Phase 4: Cutover (agent, then operator)

Do Phase 4 and Phase 5 in one sitting, so that the scheduled workflows stay paused for as short a time as possible.

1. Check that nothing is running: `gh run list -R Grumlebob/BlazorAutoAppTemplate --status in_progress` and `--status queued` must both be empty.
2. Pause the scheduled workflows that read release markers or registry labels:
   ```bash
   for w in registry-retention.yml localsinglenode-maintenance.yml localcluster-docker-maintenance.yml; do
     gh workflow disable "$w" -R Grumlebob/BlazorAutoAppTemplate
   done
   ```
   Record in §11 that they are disabled. **They must be re-enabled in Phase 6.6, even if a later phase fails.**
3. Record the rename time: `date -u +%Y-%m-%dT%H:%M:%SZ`. Write it in §11 as `T_RENAME`. Phase 6 deletes only GHCR versions created before this time.
4. Rename the repository: `gh repo rename GrumPlates -R Grumlebob/BlazorAutoAppTemplate --yes`. Verify with `gh api repos/Grumlebob/GrumPlates --jq .full_name`, which must print `Grumlebob/GrumPlates`. From here on, use `-R Grumlebob/GrumPlates`.
5. Update the remotes:
   ```bash
   git remote set-url origin https://github.com/Grumlebob/GrumPlates.git
   MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -lc 'git -C ~/src/BlazorAutoAppTemplate remote set-url origin https://github.com/Grumlebob/GrumPlates.git'
   git -C /c/Users/jgrum/Documents/Programming/Csharp/Portfolio remote set-url upstream https://github.com/Grumlebob/GrumPlates.git
   git -C /c/Users/jgrum/Documents/Programming/Csharp/CarbonCalculator remote set-url upstream https://github.com/Grumlebob/GrumPlates.git
   git fetch origin
   ```
6. Check that both runners survived the rename: `gh api repos/Grumlebob/GrumPlates/actions/runners --jq '.runners[]|"\(.name) \(.status)"'` must list `node-main-books online` and `node-demo-books online`. **STOP** if either is offline after 5 minutes: re-registering a runner needs the operator's sudo on that node (`Deployment/LocalSingleNode/Scripts/install-github-runner.sh` or `Deployment/LocalCluster/Scripts/install-github-runner.sh`). Do not continue to step 7 without both runners.
7. **OPERATOR: rewrite the node ownership markers.** The agent saves the script below as `Plans.local/GrumPlatesRename/rewrite_node_markers.py` and copies it to node-demo with `scp -F ~/.ssh/localsinglenode/8bfb4c4094be2598.conf Plans.local/GrumPlatesRename/rewrite_node_markers.py node-demo:/tmp/`. The operator copies it the same way to each LocalCluster node (192.168.0.52, .7, .59, .24). On **each** node, the operator runs:
   ```bash
   sudo python3 /tmp/rewrite_node_markers.py            # dry run: prints what would change
   sudo python3 /tmp/rewrite_node_markers.py --apply    # rewrites in place
   ```
   Expected on node-demo: changes in `/etc/localsinglenode/apps/books.json`, `/etc/localsinglenode/apps/books-react.json`, at least one `/etc/books*/public.json`, `/opt/books/release.json`, `/opt/books-react/release.json`, the `previous.json` files when present, and `/home/deploy/actions-runner-books*/.runner`. Expected on LocalCluster nodes: `/opt/books/release.json` (+ `previous.json`) on the app servers, `/etc/localcluster/apps/books.env` where present, and `/opt/actions-runner-books/.runner` on node-main. The "other files still mentioning the old URL" list should be empty; paste it into §11 if not. The script never touches CarbonCalculator or Portfolio files: it only reads the listed `books`/`books-react` paths, and its regex matches only the template URL.
   ```python
   #!/usr/bin/env python3
   """One-off GrumPlates rename: point node ownership markers at the renamed repository.

   Dry run by default. --apply rewrites matching files in place, which keeps their
   owner, group, mode and inode. --cleanup-orphans (after Phase 5) removes
   old-name folders, but only when a folder with the new name exists next to them.
   """
   import argparse
   import json
   import pathlib
   import re
   import shutil

   OLD = re.compile(r"https://github\.com/grumlebob/blazorautoapptemplate(?![A-Za-z0-9_.-])", re.IGNORECASE)
   NEW = "https://github.com/Grumlebob/GrumPlates"
   APPS = ("books", "books-react")
   BOM = b"\xef\xbb\xbf"


   def marker_files():
       for app in APPS:
           yield pathlib.Path(f"/etc/localsinglenode/apps/{app}.json")
           yield pathlib.Path(f"/etc/{app}/public.json")
           yield pathlib.Path(f"/etc/localcluster/apps/{app}.env")
           yield pathlib.Path(f"/opt/{app}/release.json")
           yield pathlib.Path(f"/opt/{app}/release-state/previous.json")
       for pattern in ("/opt/actions-runner-books*/.runner", "/home/deploy/actions-runner-books*/.runner"):
           yield from sorted(pathlib.Path("/").glob(pattern.lstrip("/")))


   def rewrite(path, apply):
       if path.is_symlink():
           print("REFUSED symlink:", path)
           return
       if not path.is_file():
           return
       data = path.read_bytes()
       bom = data.startswith(BOM)
       text = data[len(BOM):].decode("utf-8") if bom else data.decode("utf-8")
       new, count = OLD.subn(NEW, text)
       if not count:
           print("unchanged:", path)
           return
       if path.suffix == ".json" or path.name == ".runner":
           json.loads(new)  # never write invalid JSON
       print(("REWRITE " if apply else "would rewrite ") + f"{path} ({count} occurrence(s))")
       if apply:
           with open(path, "r+b") as handle:
               handle.write((BOM if bom else b"") + new.encode("utf-8"))
               handle.truncate()


   def leftovers():
       roots = [pathlib.Path(p) for p in ("/etc/localsinglenode", "/etc/localcluster", "/etc/books",
                                          "/etc/books-react", "/opt/books", "/opt/books-react")]
       skip = {"release-payloads", "backups", "node_modules"}
       for root in roots:
           if not root.is_dir():
               continue
           for path in root.rglob("*"):
               if any(part in skip for part in path.parts) or len(path.relative_to(root).parts) > 3:
                   continue
               if path.is_file() and not path.is_symlink() and path.stat().st_size < 1_000_000:
                   try:
                       if OLD.search(path.read_text(encoding="utf-8", errors="ignore")):
                           yield path
                   except OSError:
                       pass


   def cleanup_orphans(apply):
       pairs = []
       for app in APPS:
           base = pathlib.Path(f"/opt/{app}/release-payloads")
           if base.is_dir():
               pairs.append((base, "grumlebob-blazorautoapptemplate", "grumlebob-grumplates"))
       for work in list(pathlib.Path("/opt").glob("actions-runner-books*/_work")) + \
               list(pathlib.Path("/home/deploy").glob("actions-runner-books*/_work")):
           pairs.append((work, "blazorautoapptemplate", "grumplates"))
       reports = pathlib.Path("/home/deploy/.local/state/github-actions-reports/grumlebob")
       if reports.is_dir():
           pairs.append((reports, "blazorautoapptemplate", "grumplates"))
       for parent, old_name, new_name in pairs:
           children = {child.name.casefold(): child for child in parent.iterdir()}
           old, new = children.get(old_name), children.get(new_name)
           if old is None:
               continue
           if old.is_symlink() or not old.is_dir():
               print("REFUSED non-directory:", old)
           elif new is None:
               print("kept (no new-name sibling yet):", old)
           else:
               print(("REMOVE " if apply else "would remove ") + str(old))
               if apply:
                   shutil.rmtree(old)


   parser = argparse.ArgumentParser()
   parser.add_argument("--apply", action="store_true")
   parser.add_argument("--cleanup-orphans", action="store_true")
   args = parser.parse_args()
   if args.cleanup_orphans:
       cleanup_orphans(args.apply)
   else:
       for marker in marker_files():
           rewrite(marker, args.apply)
       print("other files still mentioning the old URL:")
       for path in leftovers():
           print("  ", path)
   ```
8. Merge the PR (squash) as soon as the operator confirms that step 7 is done on every node: `gh pr merge <n> -R Grumlebob/GrumPlates --squash --delete-branch`. Then wait for `build-test-push` on the new `main` commit. It must be green. That run publishes the first payloads labelled `https://github.com/Grumlebob/GrumPlates`. Record the merge SHA as `S1` in §11.

## Phase 5: Deploy twice (agent, needs the authorisation in §11)

Each instance is deployed twice from `S1`. The first deploy replaces the current release, and the second makes the recovery marker (`previous.json`) point at a new-label image too. Without the second deploy, release status would keep protecting old-label images that Phase 6 deletes.

1. LocalCluster: `gh workflow run cd-localcluster.yml -R Grumlebob/GrumPlates --ref main -f run_migrations=false -f target_sha=<S1>`. Wait for success. Then dispatch it again with the same inputs and wait for success.
2. LocalSingleNode primary: `gh workflow run cd-localsinglenode.yml -R Grumlebob/GrumPlates --ref main -f app_instance=primary -f run_migrations=false -f target_sha=<S1>`, twice, waiting for each to finish.
3. LocalSingleNode additional: the same with `-f app_instance=additional`, twice.
4. Use `run_migrations=false`, because the rename adds no migration. If a deploy fails with "pending migrations" or similar, re-run that deploy with `run_migrations=true`.
5. If a deploy fails with "Require existing release marker to belong to this repository", "Single-node app marker belongs to a different repository or root", "Public Caddy site has no matching repository ownership" or "Public deployment identity differs", the rewrite in Phase 4.7 missed a file on that node. Ask the operator to re-run the dry run there and send the output. Do not edit node files any other way.
6. If the second deploy of the same SHA is refused or skipped, ask the operator to run `sudo rm /opt/<app>/release-state/previous.json` on the affected node(s) instead. The status check accepts a missing recovery marker.
7. Verify. Dispatch `release-status.yml` for all three instances (as in Phase 0.4, with `-R Grumlebob/GrumPlates`). All must succeed, and their output must show both the current and the recovery release with source `https://github.com/Grumlebob/GrumPlates`. Then check the public site: `curl -fsS https://demo.jacobgrum.com/health/ready`. Record the run URLs in §11.

## Phase 6: Retire old registry versions and resume schedules (operator + agent)

1. **OPERATOR:** `gh auth refresh -h github.com -s delete:packages` and approve in the browser.
2. Agent: list the deletion candidates (versions created before `T_RENAME`, never the bootstrap manifest) into the scratchpad:
   ```bash
   T_RENAME='<from §11>'
   KEEP='sha256:25fef0757d76c56cd980dca6cde1e156ab7a2daa902306ab48da4e12a6e7343f'
   OUT="$SCRATCH/ghcr-candidates"; mkdir -p "$OUT"
   for p in books books-react private-books-release-payload private-books-react-release-payload; do
     gh api --paginate "/users/Grumlebob/packages/container/$p/versions?per_page=100" \
       --jq ".[] | select(.created_at < \"$T_RENAME\" and .name != \"$KEEP\") | \"\(.id) \(.name) \(.created_at)\"" \
       > "$OUT/$p.txt"
     printf '%s: %s candidates, %s total\n' "$p" "$(wc -l < "$OUT/$p.txt")" \
       "$(gh api --paginate "/users/Grumlebob/packages/container/$p/versions?per_page=100" --jq '.[].id' | wc -l)"
   done
   ```
   **STOP** if a package would lose every version, or if any digest that Phase 5.7 release-status reported as current or recovery appears in a candidate file (`grep -F '<digest>' "$OUT"/*.txt` must print nothing for each).
3. Delete the candidates:
   ```bash
   for p in books books-react private-books-release-payload private-books-react-release-payload; do
     while read -r id _; do
       gh api -X DELETE "/users/Grumlebob/packages/container/$p/versions/$id" || echo "FAILED $p $id"
     done < "$OUT/$p.txt"
   done
   ```
   Re-run the listing from step 2: every candidate file must now be empty.
4. Delete the two legacy public payload packages that nothing deploys from. First check that the template does not use them outside tests: `git grep -nE '(^|[^-])books(-react)?-release-payload' -- ':!Plans/*' | grep -v '/Tests/'` must print nothing. Then:
   ```bash
   gh api -X DELETE /users/Grumlebob/packages/container/books-release-payload
   gh api -X DELETE /users/Grumlebob/packages/container/books-react-release-payload
   ```
5. Check the packages are still linked to the renamed repository: `gh api "/users/Grumlebob/packages?package_type=container" --jq '.[]|"\(.name) \(.repository.full_name)"'` must show `Grumlebob/GrumPlates` for `books`, `books-react`, `private-books-release-payload` and `private-books-react-release-payload`.
6. Resume the schedules (always do this, even if steps 2–5 failed):
   ```bash
   for w in registry-retention.yml localsinglenode-maintenance.yml localcluster-docker-maintenance.yml; do
     gh workflow enable "$w" -R Grumlebob/GrumPlates
   done
   ```
7. Dispatch `registry-retention.yml` once without applying (`gh workflow run registry-retention.yml -R Grumlebob/GrumPlates --ref main`) and wait. It must succeed. If it fails with "registry payload belongs to a different repository", a pre-rename version is left over: find it in that package and delete it as in step 3. Then dispatch `localsinglenode-maintenance.yml` and `localcluster-docker-maintenance.yml` once with their default inputs; both must succeed. Record the URLs in §11.

## Phase 7: Clean up leftovers (agent; one optional operator step)

1. Local Docker data from the old project names. This is development data only, and the rename approval covers removing it. Remove only the exact names listed:
   ```bash
   docker volume ls --format '{{.Name}}' | grep -E '^(blazorautoapp(-codex)?_|sonarqube-blazorautoapptemplate-5b8fdacf-)' > "$SCRATCH/old-volumes.txt"
   cat "$SCRATCH/old-volumes.txt"
   while read -r v; do
     [ -z "$(docker ps -aq --filter volume="$v")" ] || { echo "IN USE: $v"; continue; }
     docker volume rm "$v"
   done < "$SCRATCH/old-volumes.txt"
   ```
   Never use `docker volume prune` or `docker system prune` (`AGENTS.md`). If a volume is in use, stop that container with `docker compose -p <project> down` (without `--volumes`), then remove the volume.
2. Old Sonar namespace: `rm -rf "$LOCALAPPDATA/BlazorAutoAppQuality/SonarQube/blazorautoapptemplate-5b8fdacf"`, then remove `BlazorAutoAppQuality` if it is empty. The next quality audit creates a fresh `GrumPlatesQuality/SonarQube/grumplates-<hash>` stack. Sonar history is not migrated (`docs/Quality/SonarQubeMaintenance.md`: "A fork or rename does not move or delete the old namespace").
3. **OPERATOR (optional, frees disk only):** on node-demo and node-main, after at least one successful run under the new name: `sudo python3 /tmp/rewrite_node_markers.py --cleanup-orphans` (dry run), then add `--apply`. It removes the old runner work folders, the old release-payload pin roots and the old CI report folder, but only where the new-name folder already exists.
4. Retire the completed diagnostic-archive pruner in a separate small code PR. `Deployment/Common/Scripts/prune-archived-diagnostic-artifacts.py` derives the expected archive name from the repository name (`<repo>-legacy-diagnostics-20261017.zip`), and its manifest names `Grumlebob/BlazorAutoAppTemplate`, so it can no longer pass. Its job is done: the repository had 0 Actions artifacts on 2026-10-28. Steps:
   1. Branch `chore/retire-diagnostic-archive-pruner` from `main`.
   2. Remove `Deployment/Common/Scripts/prune-archived-diagnostic-artifacts.py`, `Deployment/Common/Scripts/Tests/test_prune_archived_diagnostic_artifacts.py`, and `Plans/ZeroCostDiagnosticArchiveManifest-20261017.json`.
   3. In `.github/workflows/localsinglenode-maintenance.yml`, remove the `prune_archived_diagnostics` input and the step "Prune archived diagnostic artifacts under the shared deployment lock". Remove the test's line from `ci.yml` and from the gate (`~/bin/repo-gate.sh` lists commands by name but skips missing files).
   4. In `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py`, replace the rules that require the manifest (around the "exact preserved archive manifest" entry) with a rule that the workflow has no `prune_archived_diagnostics` input. `AGENTS.md` forbids just deleting a rule.
   5. `git grep -n -i 'archived.diagnostic\|ZeroCostDiagnosticArchive\|prune_archived' -- ':!Plans/*'` must print nothing except the new audit rule.
   6. Run the full gate, open the PR, wait for green `build-test-push`, merge, and verify on `origin/main`.

## Phase 8: Rename the local folder (operator closes apps; agent runs from the parent folder)

1. **OPERATOR:** close everything that uses `C:\Users\jgrum\Documents\Programming\Csharp\BlazorAutoApp` (see §4.3). Then start a new agent session in `C:\Users\jgrum\Documents\Programming\Csharp`.
2. `cd /c/Users/jgrum/Documents/Programming/Csharp && mv BlazorAutoApp GrumPlates`. If Windows reports the folder is in use, something is still open: ask the operator, and never use force.
3. `git -C GrumPlates status --short --branch` must be clean and on `main`.
4. Local ignored settings: in `GrumPlates/.env`, change `App__Name=BlazorAutoApp` to `App__Name=GrumPlates` and the header comment `# Local Docker environment for BlazorAutoApp` to `GrumPlates`. Change nothing else in `.env`.
5. Codex trust entry: in `C:\Users\jgrum\.codex\config.toml`, rename the table header `[projects.'C:\Users\jgrum\Documents\Programming\Csharp\BlazorAutoApp']` to `...\Csharp\GrumPlates']`, and keep `trust_level = "trusted"`.
6. Claude Code project memory. Move the folder contents:
   ```bash
   OLD=~/.claude/projects/C--Users-jgrum-Documents-Programming-Csharp-BlazorAutoApp/memory
   NEW=~/.claude/projects/C--Users-jgrum-Documents-Programming-Csharp-GrumPlates/memory
   mkdir -p "$NEW" && cp -p "$OLD"/* "$NEW"/ && ls "$NEW"
   ```
   Then edit the copies: in `repo-gate-wsl-invocation.md`, change `GATE_SRC` paths to `/mnt/c/Users/jgrum/Documents/Programming/Csharp/GrumPlates`; in `fix-template-upstream.md` and any other memory that names `Grumlebob/BlazorAutoAppTemplate`, use `Grumlebob/GrumPlates`. Keep the old folder until the operator has opened one session in the new path and seen the memories load. Do not edit `~/.claude.json`: Claude Code adds the new path itself, with a trust prompt.
7. WSL clone: `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -lc 'mv ~/src/BlazorAutoAppTemplate ~/src/GrumPlates && git -C ~/src/GrumPlates status -sb | head -1'`.
8. Smoke test the renamed checkout: `cd GrumPlates && pwsh -File Scripts/RunLocal.ps1`. The local stack starts under Compose project `grumplates`, and Grafana's Alloy collector sees the containers (filter `grumplates`). Stop it afterwards with the script's documented stop option, without `--volumes`.

## Phase 9: Downstream follow-ups (agent, no deadline)

1. Portfolio and CarbonCalculator: the `upstream` remotes were updated in Phase 4.5. Links to `github.com/Grumlebob/BlazorAutoAppTemplate` in their docs keep working through the redirect. Update them in each repository's next ordinary docs PR, not in a dedicated PR.
2. When porting template changes into a downstream repo, map `GrumPlates*` paths to that product's names, for example `GrumPlates/…` to `Portfolio/…`.
3. ImprovedDb: nothing to do.

## Phase 10: Closeout (agent)

1. `git fetch --prune origin`. Check that `origin/main` contains the rename commit `S1` and, if done, the Phase 7.4 commit, and that exact-main CI is green for both.
2. `git grep -nIiE 'blazorautoapp|blazor-auto-app' -- ':!Plans/*'` on `origin/main` prints nothing.
3. Fill in §11. Record each deleted branch's full SHA (`chore/rename-grumplates`, `chore/retire-diagnostic-archive-pruner`). Set Status at the top to **complete**.
4. Commit the plan update as a docs-only PR with `[skip ci]` in the title, following `AGENTS.md`.

## 11. Record

| Item | Value |
| --- | --- |
| Deploy authorisation (who, when, scope) | Operator (grumlebob), 2026-10-28, chat: "yea. lets do it proper. full permissions"; covers all Phase 5 deploys |
| Phase 0.4 baseline release-status runs | All success: 40658161609 (localcluster), 40658169977 (primary), 40658178296 (additional) |
| Workflows disabled at / re-enabled at | 2026-10-28T08:40:32Z / 2026-10-28T13:11:12Z |
| `T_RENAME` | 2026-10-28T08:40:36Z |
| Rename PR / merge SHA `S1` / main CI run | #389 / `9cb1961f8959b3e7bf7a8b30f37320ed2bb03cef` / 40663362881 (success) |
| Node marker rewrite done (node, operator confirmation) | Agent, 2026-10-28, with sudo from the main PC: LocalCluster .52 (`books.env`, runner `.runner`), .7 and .59 (`books.env`, `release.json`, `previous.json`), .24 (`books.env`); node-demo (10 files incl. both apps' markers, `public.json`, runner `.runner`). Leftover scan empty. |
| Deploy runs (LocalCluster ×2, primary ×2, additional ×2) | LocalCluster from `S1`: 40668876218, 40671622403. node-demo from `S4` (`fe457e0599022001e4c0faab5fa1c2c5567eb894`, after the fixes below), `run_migrations=true` then `false`: primary 40690860276, 40691512860; additional 40691183827, 40691836206. All success. |
| Phase 5.7 release-status runs and public health | 40692158896, 40692168528, 40692177830 success; all 8 current/recovery markers name `https://github.com/Grumlebob/GrumPlates`; `demo.jacobgrum.com/health/ready` 200 |
| GHCR versions deleted per package | `books` 626, `books-react` 327, `private-books-release-payload` 15, `private-books-react-release-payload` 15 (0 failures; bootstrap manifest kept); packages `books-release-payload` and `books-react-release-payload` deleted |
| Phase 6.7 retention/maintenance runs | Retention 40694141788, LocalCluster Docker maintenance 40694165550, LocalSingleNode maintenance 40695174444 (after #394's unit fix was applied on node-demo): success |
| Phase 7.4 PR / merge SHA | Folded into #389 (commit `4cce746a`): PR CI failed on the pruner's repository-bound manifest test after the GitHub rename |
| Deleted branches (full SHA) | `chore/rename-grumplates` `4cce746ad54ca866ad963b3161ddaad1538394f5`; `fix/localsinglenode-openssl3-data-protection` `03f2e0b38428d60163db93902e7a1cb4b6ac6ac9`; `fix/localsinglenode-collision-compose-env` `6bc361d75fd4306ae98ee8a4d21b8a084f70599f`; `fix/localsinglenode-compose-env-helpers` `6320782d8f32ce781f785f5143a25463a594810c`; `fix/localsinglenode-backup-deploy-group` `d6c7789a0e9b7456b6f46f1b8b83d05f735d0677` |

### Deviations and findings

- The GitHub rename ran during the local gate (before the PR), so the marker rewrite could overlap. PR CI works after a rename.
- The local gate's tools were stale (actionlint without `queue:` support, Node 24 for a Node 26.12.1 pin). `~/bin/repo-gate.sh` now uses `Scripts/CI/run-actionlint.sh` and the `engines.node` version.
- node-demo had not been deployed since 2026-10-16, so the cutover exposed template defects that blocked every LocalSingleNode deploy, independent of the rename:
  1. `secrets.yml` predated `vault_data_protection_certificate_password` (#320). The agent added a generated passphrase to `/etc/books{,-react}/secrets.yml`; #391 makes the deploy fail with a clear message instead.
  2. `openssl req -aes256` is rejected by OpenSSL 3.0 (Ubuntu 24.04): fixed in #391.
  3. The collision check and `backup.py`, `restart-app-check.py`, `verify-release-identity.sh` ran `docker compose` without `.compose.env`: fixed in #392 and #393. CarbonCalculator still lacks the collision-check part: Grumlebob/CarbonCalculator#412.
  4. The backup unit's `Group=` dropped `deploy`, so nightly backups could not read the certificate: #394 (applied to node-demo's installed units).
  Several of these were already fixed in CarbonCalculator and had not been ported back to the template.
- CodeQL dismissals were re-applied to the renamed paths (alerts 16–22, same reasons).
- Old-name orphans removed with `--cleanup-orphans` on node-demo and node-main. Old Sonar stack (containers, volumes, network, folder) removed. The `blazorautoapp_*` dev volumes are left for Phase 8.
- Phase 8 done 2026-10-28: folder moved to `...\Csharp\GrumPlates`, WSL clone to `~/src/GrumPlates`, `.env` `App__Name` updated, Codex trust and Claude memory moved, the 11 `blazorautoapp*` dev volumes removed. The smoke test ran under Compose project `grumplates` and `/health/ready` returned 200. It needed process-only overrides: host ports 5433 and 7186 were taken by other local projects, and machine-wide `POSTGRES_*`/`Database__*` variables override `.env`. Two `Scripts/RunLocal.ps1` defects were found: the health URL ignores an `APP_HTTPS_HOST_PORT` override, and `docker logs --since` gets a culture-formatted time (`14.48.39`), so failures print no logs.
