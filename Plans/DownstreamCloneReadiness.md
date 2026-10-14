# Downstream clone readiness after Portfolio

Status: complete on 2026-10-14 once the PR in C8 is merged and verified; the merge record is in that PR's description.
Owner request (2026-10-14): after the Portfolio delivery, clean up leftovers (A), make `gh` safe in the Portfolio checkout (B), and write the clone lessons into the template (C) before the next product is cloned.

## 1. Outcome

When this plan is complete:

- Workspace leftovers from the Portfolio and React-delivery sessions are removed or reported with a concrete reason to keep them. Every deleted branch's full SHA is recorded in § 9.
- Plain `gh` commands in the Portfolio checkout act on Grumlebob/Portfolio, not on the template.
- The template documents how to turn a fork into a standalone product, how to remove the Blazor profile from a clone, and the two process rules that cost the Portfolio delivery time.
- The documentation PR is merged with `[skip ci]`, its content is verified on `origin/main`, and the merge commit is recorded in the PR description.

## 2. Scope

In scope:

- Local cleanup in `C:/Users/jgrum/Documents/Programming/Csharp` (template checkout, Portfolio checkout and the `ReactFrontendDelivery-*` folders).
- Template remote branches whose merged PR head equals the branch tip.
- Local `gh` configuration for the Portfolio checkout.
- Template Markdown: one new plan, two new guides, the fork guide and `AGENTS.md`.

Out of scope. Do not do these, even if they look related:

- Planning or building the next product (for example CarbonCalculator). Its delivery starts from its own prompt.
- Any code, workflow, script or configuration change. This is a docs-only plan; a non-Markdown change turns it into a code PR with the full gate.
- Any deployment, node, Cloudflare or runner change.
- Portfolio repository content. Portfolio keeps its own plans until its owner decides otherwise (see § 8).
- Branches, folders or repositories this plan does not list. Report them instead.

## 3. Executor rules

Read these before every workstream. They apply to any agent, including a less capable one.

1. **Look before deleting.** Run the listed verification command and compare its output with the expected value in the step. If anything differs, stop that step, write what you saw into § 9, and continue with the next independent step.
2. **Never force.** No `git push --force`, `git worktree remove --force`, `git clean -fdx`, or `rm -rf` on a path the step does not name exactly. `git branch -D` is allowed only for a branch whose content the step has verified as integrated.
3. **Record before removing.** Write each branch's full 40-character SHA into § 9 before deleting it. A recorded SHA can be restored with `git branch <name> <sha>` while the commit is still reachable on GitHub or in a local clone.
4. **Squash merges hide ancestry.** A squash-merged branch is never an ancestor of `main`. Prove integration with `gh pr view` (state `MERGED` and `headRefOid` equal to the branch tip), not with `git branch --merged`.
5. **Use Git Bash** for the commands below. Paths use `/c/Users/jgrum/...`. In PowerShell, translate the syntax instead of mixing shells.
6. **`gh` needs an explicit repository** until workstream B is done: pass `-R Grumlebob/<repo>` on every `gh` command.
7. **Docs-only PR rules** come from `AGENTS.md`: no build or test run is required, but run `git diff --check` and the deployment audit (step C7), put `[skip ci]` in commit messages and the squash title, and verify the integrated content on `origin/main` afterwards.
8. **Do not touch:** `ImprovedDb*` folders, `JDForecasting`, `KinoJoin`, `BlazorTusReliableUpload`, the Portfolio `Plans.local/` folder and any `Plans.local/` content in the template.

## 4. Baseline verified on 2026-10-14

| Fact | Evidence |
| --- | --- |
| Portfolio delivery is complete apart from owner decisions | Portfolio `main` `fe52eff`, Progress § Current checkpoint; release `b35f065`, CD run 38457663765 success |
| Portfolio has no open PRs; its remote has only `main` | `gh pr list -R Grumlebob/Portfolio`; `git ls-remote --heads` |
| Template mirror is current | Template `main` `6e8750de` (#261); mirror differs only by its banner |
| `gh` in the Portfolio checkout resolves to the template | `gh repo view --json nameWithOwner` printed `Grumlebob/BlazorAutoAppTemplate`, because `gh` prefers a remote named `upstream` |
| Stale nested clone `BlazorAutoApp/Portfolio/` | Untracked in the template checkout. Branch `feat/vs1-a-content-compiler` at `71fd04978f624b1f821c745cd612dbef4a4d08fe` (WIP, superseded by Portfolio #17). `origin` is a WSL path. No stash, no untracked files apart from build output |
| 22 local-only Portfolio branches | Their remote branches were deleted at merge |
| Worktree `ReactFrontendDelivery-P3-AccountFreeContract` | Branch `feat/react-p3-account-free-contract` at `faa75d53…`, PR #137 merged as `12cca817`. Holds an uncommitted, superseded 7-line ledger edit to `Plans/ReactFrontendProfile.md` |
| Clone `ReactFrontendDelivery-DownstreamSeed` | Clone of `Grumlebob/ReactFrontendDemo`, which no longer exists on GitHub. `main` `4cd9c97` is an ancestor of template `main`; clean, no stash, no unique commits |
| Three empty folders `ReactFrontendDelivery-{P5-ReactScaffold,P7-AcceptanceContract,P7-CI};C` | Path-conversion artifacts from 2026-10-11 |
| Template has 62 remote and 52 local branches | `git ls-remote --heads origin`, `git branch` |

## 5. Workstream A: cleanup

### A1. Remove the nested Portfolio clone

1. `cd /c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp/Portfolio`
2. Verify, expecting exactly the noted results:
   - `git rev-parse HEAD` → `71fd04978f624b1f821c745cd612dbef4a4d08fe`
   - `git branch --format='%(refname:short)'` → only `feat/vs1-a-content-compiler`
   - `git stash list` → empty
   - `git status --short --ignored | grep -vE '(^|/)(bin|obj|node_modules|TestResults)/'` → empty
   - In the real Portfolio checkout: `git -C /c/Users/jgrum/Documents/Programming/Csharp/Portfolio cat-file -t 71fd049` → `commit`
3. Record the SHA in § 9, then `cd ..` and `rm -rf -- Portfolio` from `/c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp`. Only this exact relative path.
4. Verify: `git -C /c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp status --short` no longer lists `Portfolio/`.

### A2. Delete Portfolio's merged local branches

1. `cd /c/Users/jgrum/Documents/Programming/Csharp/Portfolio && git fetch --prune origin`.
2. For each local branch other than `main`, print its tip and its PR:
   ```bash
   for b in $(git branch --format='%(refname:short)' | grep -v '^main$'); do
     tip=$(git rev-parse "$b")
     pr=$(gh pr list -R Grumlebob/Portfolio --state all --head "$b" --json number,state,headRefOid \
          -q '.[] | "\(.number) \(.state) \(.headRefOid)"' | head -1)
     echo "$b $tip $pr"
   done
   ```
3. A branch is deletable only when its PR state is `MERGED` and the PR `headRefOid` equals `tip`. Copy those lines into § 9 first.
4. Delete each deletable branch with `git branch -D <branch>`.
5. Any other branch (no PR, closed PR, or different head) is kept. Record it in § 9 with its tip and the reason.
6. Verify: `git branch` lists `main` plus only the recorded keepers.

### A3. Close the finished React-delivery P3 worktree

1. Archive the uncommitted edit before touching it:
   ```bash
   W=/c/Users/jgrum/Documents/Programming/Csharp/ReactFrontendDelivery-P3-AccountFreeContract
   A=/c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp/Plans.local/Archive/react-p3-worktree-20261014.patch
   mkdir -p "$(dirname "$A")" && git -C "$W" diff > "$A" && sha256sum "$A"
   ```
   Record the SHA-256 in § 9. The edit only updates an old ledger that is now complete on `main`, so it is superseded.
2. Verify the PR: `gh pr view 137 -R Grumlebob/BlazorAutoAppTemplate --json state,headRefOid` → `MERGED`, `faa75d533022918188a5e4f0236f67cd5a88703f`. Verify the worktree tip: `git -C "$W" rev-parse HEAD` → the same SHA.
3. Discard the archived edit: `git -C "$W" restore Plans/ReactFrontendProfile.md`. Then `git -C "$W" status --short` → empty.
4. From the template checkout: `git worktree remove ../ReactFrontendDelivery-P3-AccountFreeContract` (no `--force`). If it refuses, stop and record the message.
5. Delete the branch locally (`git branch -D feat/react-p3-account-free-contract`) and remotely (`git push origin --delete feat/react-p3-account-free-contract`). Record its SHA first.

### A4. Remove the orphaned DownstreamSeed clone

1. `cd /c/Users/jgrum/Documents/Programming/Csharp/ReactFrontendDelivery-DownstreamSeed`.
2. Verify:
   - `gh repo view Grumlebob/ReactFrontendDemo` → "Could not resolve to a Repository";
   - `git rev-parse HEAD` → starts with `4cd9c97`;
   - `git -C ../BlazorAutoApp merge-base --is-ancestor 4cd9c97 origin/main` exits 0;
   - `git stash list` is empty;
   - `git status --short --ignored` is empty;
   - `git branch` lists only `main`.
3. Record the SHA in § 9, then from `/c/Users/jgrum/Documents/Programming/Csharp` run `rm -rf -- ReactFrontendDelivery-DownstreamSeed`.

### A5. Remove the three empty artifact folders

From `/c/Users/jgrum/Documents/Programming/Csharp` run `rmdir` (not `rm -r`) on each of the three `ReactFrontendDelivery-*;C` folders. Quote the names because of the `;`. `rmdir` fails on a non-empty folder; if it does, stop and record the contents.

### A6. Prune template branches whose PRs are merged

1. `cd /c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp && git fetch --prune origin`.
2. Build a table for every remote branch except `main`. Give each one its tip, PR number, PR state and PR head:
   ```bash
   git for-each-ref --format='%(refname:lstrip=3) %(objectname)' refs/remotes/origin | grep -vE '^(HEAD|main) ' |
   while read b tip; do
     pr=$(gh pr list -R Grumlebob/BlazorAutoAppTemplate --state all --head "$b" --json number,state,headRefOid \
          -q '.[] | "\(.number) \(.state) \(.headRefOid)"' | head -1)
     echo "$b $tip ${pr:-none}"
   done | tee Plans.local/Archive/template-branches-20261014.txt
   ```
3. Delete a remote branch only when its PR is `MERGED` and its PR head equals the tip. Also check that no open PR uses the branch as its base: `gh pr list -R Grumlebob/BlazorAutoAppTemplate --base <branch>` → empty. Then run `git push origin --delete <branch>`. The archived table is the SHA record. Copy the deleted names and tips into § 9.
4. Keep every other remote branch: no PR, open PR, closed-unmerged PR or moved tip. Some belong to other people or live tasks (for example `HullImages`, `coord/node-inventory-handoff`). List them in § 9 with the reason.
5. Local template branches: delete a local branch with `git branch -D` only when it has no unique commits against a merged PR head (the same rule), or when its upstream was deleted in step 3 and the local tip equals the deleted tip. Keep and report the rest.
6. Do not delete the primary checkout's `main`. Afterwards, fast-forward it: `git switch main && git merge --ff-only origin/main`, but only if `git status --short` is clean.

### A7. Final workspace check

- `git -C BlazorAutoApp worktree list` lists only the primary checkout, plus any recorded keeper.
- `ls /c/Users/jgrum/Documents/Programming/Csharp` no longer shows the removed folders.
- Record the results in § 9.

## 6. Workstream B: make `gh` target the right repository

1. In the Portfolio checkout: `gh repo set-default Grumlebob/Portfolio`.
2. Verify: `gh repo view --json nameWithOwner -q .nameWithOwner` → `Grumlebob/Portfolio`, and `gh pr list` shows Portfolio PRs (currently none).
3. In the template checkout: `gh repo view --json nameWithOwner -q .nameWithOwner` → `Grumlebob/BlazorAutoAppTemplate`. It has no `upstream` remote, so it needs no change. If it ever gets one, run `gh repo set-default Grumlebob/BlazorAutoAppTemplate`.
4. Record both outputs in § 9. The setting is stored in the checkout's `.git/config` (`remote.<name>.gh-resolved = base`), so it is local and not committed.

## 7. Workstream C: write the clone lessons into the template

Branch: `docs/downstream-clone-readiness` from `origin/main`. Every changed file must be Markdown, so this is a docs-only PR.

Editorial rules, from [ThinSlicedDocumentation](ThinSlicedDocumentation.md) and `AGENTS.md`:

- Durable docs describe current template behavior. Link canonical owners instead of repeating them.
- A new file must shorten a concrete task's reading. Here that task is "make a standalone React product from this template", which currently has no route.
- Name real template paths only after checking that they exist on `origin/main` (`git ls-files <path>`). Use generic names (`<Product>`) in examples. Portfolio PRs may be linked as worked examples because they explain template behavior.
- Never include node addresses, host names, tokens or private paths.

### C1. New guide `docs/Frontend/ReactOnlyClone.md`

Purpose: remove the Blazor profile from a clone without leaving builds, CI, audits or docs that still expect it. The source is Portfolio PR #11 and its recorded follow-ups (D-EXEC-02).

Required content, in this order:

1. When to use the guide, and the prerequisite: React selected per the fork guide, with a green CI.
2. Order relative to the other clone guides: React-only, then single-node-only, then the rename. Deleted code is never renamed first.
3. An inventory command and a classification table by area, covering:
   - the client project;
   - host Razor UI and account pages;
   - composition;
   - styles;
   - MSBuild;
   - Docker;
   - CI;
   - profile and release tooling;
   - the additional app instance;
   - tests;
   - browser tooling;
   - quality tooling;
   - docs and rules.
   Every path must exist on `origin/main`.
4. A numbered safe removal sequence. Move shared tooling before deleting the client, then:
   1. change entry points;
   2. delete;
   3. rewrite tests;
   4. replace audit rules (never just delete them);
   5. update docs;
   6. search again and classify what remains;
   7. run the gate, open the PR and wait for exact-head CI.
5. Deliberate boundaries: narrowing the profile resolver and release verifiers can be a later PR, and it must be recorded. Database, Redis, Identity storage and the Books sample are separate product decisions.
6. Link to Portfolio PR #11 as the worked example.

Verification:

- `git ls-files` finds every path named in the table.
- The page stays under about 700 words.
- It links the fork guide, `SingleNodeOnlyClone.md` and the local gate.

### C2. New guide `docs/StandaloneProduct.md`

Purpose: the end-to-end order for turning a fork into a product of its own. The source is Portfolio P0.2, PRs #11–#13, the clone friction log (CF01–CF04) and the Progress lessons.

Required content:

1. **Create the repository.**
   - Start from an empty repository, with Actions disabled until a runner for it exists.
   - Clone with history; `origin` points to the product and `upstream` to the template.
   - **Run `gh repo set-default` immediately**, and say why.
   - Commit a seed for identity per the fork guide.
2. **Runners and plan limits.**
   - On a personal account, self-hosted runners belong to one repository, so a machine that already runs another repository's runner needs a second registration for this repository.
   - Private repositories on GitHub Free have no branch protection or rulesets, so the required check becomes a working rule. Private images count toward the account's GitHub Packages storage.
3. **Simplification order:**
   1. seed;
   2. React-only (C1);
   3. single target (`SingleNodeOnlyClone.md`);
   4. rename, with a generic rename map;
   5. template material removal;
   6. replace the sample feature.

   Each step is its own PR. Retarget stacked PRs before merging.
4. **Template material to remove or rewrite.** A table with an action for each item:
   - `Plans/`;
   - the template-only guides, including this one;
   - README;
   - Requirements;
   - AGENTS;
   - tool folders;
   - the quality tooling;
   - the sample feature.

   Include a final search command and the rule for keeping provenance links.
5. **Public site behind Cloudflare.**
   - The React host's CSP (`script-src 'self'`) blocks scripts injected by Cloudflare JavaScript detections.
   - There are two options: a per-response nonce (Portfolio #32) or excluding the hostname from JavaScript detections.
   - Running the detection script lowered Portfolio's Lighthouse best-practices score to 81.
   - Template #259 already ignores Cloudflare edge cookies.
6. **Sharing a node with another product.**
   - Several apps can share a node.
   - `ApplicationInstances.md` covers only a second profile of the same repository.
   - A second repository on an existing node has no tested route yet. Start with the read-only readiness and collision check, and stop for an operator decision before any root command.

Verification:

- Every path and PR number exists.
- The page stays under about 900 words.
- It does not repeat the fork guide's identity table or the release contract; it links them.

### C3. Route from the fork guide

Edit `docs/HowToForkThisRepo.md`. This file is read by the deployment audit.

- Add one short section that links `StandaloneProduct.md` and `Frontend/ReactOnlyClone.md`.
- Add one sentence on `gh repo set-default` when the clone has an `upstream` remote.

Do not move or reword audited sentences. Keep the guide under 850 words (`wc -w`).

### C4. Two process rules in `AGENTS.md`

Add at most two short bullets to "Changes and checks":

- Docs-only changes still need the deployment audit when they touch `Deployment/` or `docs/`, because the audit reads Markdown. Template #260 repaired `main` after two `[skip ci]` docs commits broke it.
- Before merging a PR that other open PRs use as their base, retarget those PRs to `main` (`gh pr edit <n> --base main`); `--delete-branch` otherwise closes them.

Keep `AGENTS.md` short: add no more than about 70 words. Machine-specific gate quirks stay in private agent memory, not in tracked files.

### C5. README routing

In the root README's "Start here" table, change the fork row so that it also reaches the standalone-product guide. Keep the README's word budget (about 350 words).

### C6. Plan record

Fill § 9 as work happens. Mark this plan complete only after C8.

### C7. Verify locally

1. `git diff --check origin/main...HEAD` → no output.
2. `git diff --name-only origin/main...HEAD` → only `.md` files.
3. For every relative link in the changed files, check that the target exists. A simple check:
   ```bash
   for f in $(git diff --name-only origin/main...HEAD); do
     grep -oE '\]\([^)#]+' "$f" | sed 's/](//' | grep -vE '^https?:' |
     while read l; do [ -e "$(dirname "$f")/$l" ] || echo "BROKEN $f -> $l"; done
   done
   ```
   Links inside code blocks (including this one) are false positives; ignore them.
4. Run the deployment audit, which reads the fork guide and deployment Markdown, in WSL:
   ```bash
   MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -- bash -lc 'cd /mnt/c/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp && bash Deployment/LocalCluster/Scripts/audit-deployment.sh'
   ```
   It must report success. If it fails on a file this PR did not touch, check pristine `origin/main` first.
5. Run `wc -w` on the new and changed docs, and record the counts in the PR.

### C8. PR, merge and verify on main

1. Stage explicit paths only:
   ```bash
   git add Plans/DownstreamCloneReadiness.md docs/StandaloneProduct.md docs/Frontend/ReactOnlyClone.md docs/HowToForkThisRepo.md AGENTS.md README.md
   ```
2. Commit with `[skip ci]` in the subject. Push the branch, then open a PR whose title contains `[skip ci]`. The body lists the files, the verification results and the cleanup summary.
3. Review the complete PR diff (`gh pr diff`).
4. Merge with `gh pr merge <n> -R Grumlebob/BlazorAutoAppTemplate --squash --delete-branch --match-head-commit <head>`. Keep `[skip ci]` in the squash subject.
5. `git fetch --prune origin` and verify the integrated content: `git diff <head> origin/main -- <files>` is empty for the changed files.
6. Edit the PR description to add the merge commit and the verification. Record the deleted branch SHA in § 9 through a follow-up only if a later docs PR happens anyway. The PR description is the authoritative record of the merge.

## 8. Known gaps left for later (not this plan)

| Gap | Why it matters | Suggested owner/next step |
| --- | --- | --- |
| `Deployment/LocalCluster/Scripts/install-github-runner.sh`, `check-github-runner.sh`, `cleanup-renamed-localcluster-app.sh` and `Deployment/Cloud/Scripts/configure-github-environment.sh` use plain `gh repo view`, which resolves to `upstream` in a clone | A clone that keeps those targets could register a runner or environment on the template | Code PR: resolve the repository from `origin` the way `Deployment/LocalSingleNode/Scripts/lib/setup_status.py` does |
| No tested route for a second **repository** on a node that already serves another app | The next product may share a node | Prove it with the read-only readiness check first; document after a real run |
| The CSP nonce for Cloudflare JavaScript detections lives only in Portfolio | A template deployment behind the same zone shows a console CSP error | Owner decision; port only if a template deployment needs it |
| `Scripts/Quality` still names the Blazor client in clones | Noise in React-only clones | Handle in the clone or in a tooling PR |
| `Deployment/Common/Scripts/Tests/test_operation_source.py` `repository()` runs `git -C <temp> init` and `git config user.*` without clearing inherited `GIT_DIR`/`GIT_WORK_TREE` | Run under an exported `GIT_DIR` (hooks, some gate wrappers), it writes into the real repository's `.git/config`: on 2026-10-14 the template checkout had `user.name=Fixture`, and on 2026-10-13 a stray `core.worktree` was removed | Code PR: run fixture git commands with `GIT_*` variables removed from the environment, and add a test that the real repository's config is unchanged |
| Portfolio still carries about 13 template-era plans and a provenance README | It is not a fully standalone product | Portfolio owner decision |

## 9. Execution record

Fill in as each step completes. Use full SHAs.

```text
A1 nested clone: BlazorAutoApp/Portfolio removed 2026-10-14. Tip 71fd04978f624b1f821c745cd612dbef4a4d08fe (feat/vs1-a-content-compiler, superseded by Portfolio #17; commit present in the Portfolio checkout). The first rm left an empty folder while a shell had it as cwd; rmdir removed it.
A2 Portfolio branches deleted (name tip PR), all PR state MERGED:
  docs/authoring-handover 4f76cb40f721ae586026fcf95c841eeb59305f13 #28
  docs/final-session-checkpoint 0ee70d7308a1789559b922e7de2ff2c6441d714f #31
  docs/p0-baseline-and-import ff5b24897dd8439bf3ac4a8b32cd9c40e6264f98 #1
  docs/portfolio-node-setup-file d0675e95f239e04414c88a902ec22fb7d7abedaf #15
  docs/progress-catalog-drafts b1bc894f7100ed8886490c4d3a286c8046999335 #24
  docs/progress-vs0-implemented 2f6cc1d07709f172d7be75721072e8638569ec54 #14
  docs/record-public-launch c9f94e955ed67e4cb8c54f75cfeb0da7826c3d8a #26
  feat/launch-all-stories 1d0aef51a856514b5910f355ba425658bf878c5b #25
  feat/p0-3-studio-design-reference d58eb104e7cffef0ba4d56e6ea0b791f5270d313 #10
  feat/p7-3-portfolio-acceptance 039fb0a5568cf5c1485963b9612d95bb46880669 #21
  feat/vs1-a-content-compiler 48d7ef2c2f61b2dbc2085bda72ba8e080e817da9 #17
  feat/vs2-traceback-story fad1daaef48cd48045bae7dae1fe2f462bc117ea #19
  feat/vs2b-kinojoin-story 6d6062e54e3a7b5cac70b374c414c85b9094d82d #20
  feat/vs2c-ship-inspections-story a8d8a06039c659cbd3f6376439faace17c40c2ba #22
  feat/vs2d-more-stories d801deef62b9d4acae915dd0076eac84b351ab60 #23
  feat/vs3-file-only-runtime fab598bcd11b4a128d75fdeb73b706d167c8aae5 #18
  fix/content-lf-endings 4f745b23ab337e04202e47dbfb2a880f9ba727b6 #27
  fix/deterministic-tailwind-sources 97093da4a966d770b3a1eda75b9454c7b47366a1 #30
  fix/public-readiness-label 954ac66e630f470f3346ecf9cb4e4de52ddc9d50 #29
  Stacked branches whose local tip predates the PR's final rebased head (content verified: the final head only adds the rebase onto main and a CI browser-tools step; the local tip has nothing the final head lacks):
  feat/p1-portfolio-rename e0b185030e115862ccd3204df0ae0f88dd20ede0 #13 (final head dbc97b82edafcb64f48dc5549a90340b36584367)
  feat/p2-react-only-frontend fd2d29ca2a567f7b772f5e8bfd59124202ea8ee3 #11 (final head 6f3b0b4646bf5c224b4e44851099a0e5dc263ddb)
  feat/p3-single-node-only 45e7e8ecf5cd734760eae9586d60549fab4337e3 #12 (final head d6fa25b18ee6100d47763201fbd7147e011d299e)
A2 kept: none (Portfolio now has only main locally and remotely).
A3: patch archived at Plans.local/Archive/react-p3-worktree-20261014.patch, SHA-256 86aafdd4201a165c76ddd3509e5c4ed7132df0b1da6f9f9db0e7aabf11f157db. The worktree's ignored Plans.local notes (3 files, not present in the primary checkout) and a local dev Data Protection key were copied to Plans.local/Archive/react-p3-worktree-ignored-20261014/ and verified with SHA256SUMS. Worktree removed without --force. Branch feat/react-p3-account-free-contract faa75d533022918188a5e4f0236f67cd5a88703f (PR #137 MERGED, same head) deleted locally and on origin.
A4: ReactFrontendDelivery-DownstreamSeed removed. main and origin/main 4cd9c97ccd0c31afeac15aa51d801f2bd63a32b8 (ancestor of template main); Grumlebob/ReactFrontendDemo no longer exists; clean, no stash.
A5: three empty ReactFrontendDelivery-*;C folders removed with rmdir.
A6 template remote: 56 deleted (PR MERGED, PR head equals tip, no open PR based on them). Table archived at Plans.local/Archive/template-branches-20261014.txt (SHA-256 0539bb32fdb10fe0ec92037e829876e068aa6ab56fcb0509b2829478bce53250); names and tips listed below.
A6 kept remote: HullImages 47fdfe754eb3c612c023bc9a608136471cc60042 (no PR; tip is an ancestor of main, kept as an unknown owner's bookmark); coord/node-inventory-handoff c6a59ba3afe8afe4a041400cd088ae9c43dbf4ba (no PR, 3 commits not on main); dependabot #222 and #223 (open PRs).
A6 local: 48 deleted (44 equal to a merged PR head; fix/p14-cloudflared-service-path, review/localsinglenode-senior-review, upgrade/plan-main-pc-node-demo and HullImages are ancestors of main). List archived at Plans.local/Archive/template-local-branches-20261014.txt (SHA-256 aaee72838363b24b8c0f4d34b662d73f584343bccf6dac8d15361ef55dccfd86). Kept: coord/node-inventory-handoff (3 unique commits), preserve/shared-drafts-20261011 bf112f3b1c77420b5151daaa9d026cc768b39ea9 (1 unique commit, explicit preserve branch).
A7: removed a leaked local identity from the template's .git/config (user.name=Fixture, user.email=fixture@example.invalid, written by the test fixture in § 8); no commit by that identity exists on any ref. Template worktree list shows only the primary checkout; local main equals origin/main 6e8750de before this PR. Other folders (ImprovedDb*, JDForecasting, KinoJoin, BlazorTusReliableUpload) untouched; a new ImprovedDb-quality-plan-20261014 folder belongs to another active session.
B: Portfolio checkout: gh repo set-default Grumlebob/Portfolio; gh repo view prints Grumlebob/Portfolio (remote.origin.gh-resolved=base). Template checkout prints Grumlebob/BlazorAutoAppTemplate; no change needed.
C7: git diff --check clean; only .md files changed; relative links resolve (the plan's own code block matches the link pattern and is a known false positive); deployment audit passed in WSL Ubuntu-24.04. Words: StandaloneProduct 852, ReactOnlyClone 660, fork guide 566, AGENTS 837 (was 792), README 251.
C8: see the PR description for head, merge commit and origin/main verification.
```

Deleted template branches (full tips):

```text
Template remote branches deleted (name tip PR):
docs/portfolio-chat-handoffs-20261011 f322b0cbc4c6450ba62784d797cb27181c9a7e5b #172
docs/portfolio-contract-consistency-20261011 3599e2ebeaef6901b9ac06e4a512694a084b1955 #171
docs/portfolio-execution-plan-20261011 63eb5b645fb3c8861e4ecc9a0b78dc615d9a5e19 #170
docs/portfolio-geckobot-repo-rename-20261011 eaa7ef5a633e56a22668fd953d17a0631e92520a #167
docs/portfolio-readiness-gecko-cleanup-20261011 267a895600cfe3d0f6a037e1a18602a70dd4cc37 #164
docs/portfolio-source-refinements-20261011 b4c90de3842ccb8f24021995756f1e8bcb3ab541 #162
docs/portfolio-super-plan-20261011 ca0157143dded4cbba9ab61a6604e43822e9f1cc #159
docs/react-delivery-goal-refresh fecfe81fc45a754126a6bca345475613be7055dd #156
docs/react-demo-native-node-handoff c2dfa725399972e3b6ceb5ee1966c3a0214fc3c0 #153
docs/react-demo-node-check-results b99cb781f1af9c5360e1dc84637f78d47a9a79bc #155
docs/react-final-public-handover 31a3788a2d730af20d2d58a3a746d9a52b10b7d7 #176
docs/react-node-readiness b82677338938e0f2e371d0304b7eeb3c38aed0e8 #158
docs/react-p6-evidence ce3a3dd854e83b21b714e4b78ef2e37578b232d6 #145
docs/react-p7a-node-handoff 91ea1283ed221fda65597f98c56364a0bd20be93 #152
docs/react-single-repository-delivery c1a05258f652467fdbe16fde0adf2fa1122a3743 #165
docs/record-admin-seed-plan 8022d390ba47d03e6490e4ead33dc5452f166e49 #119
docs/remove-extra-react-repository a672f795a48101482b25682549c7f280f12b6c33 #163
docs/sonarqube-baseline c6ad9481342d52d8f9bc689689be47c665f3a61f #179
docs/sonarqube-closeout d293405e4555f62008af25e3c855e70b724814bb #180
docs/sonarqube-on-demand-quality-20261011 213e607da260ea94da993cbd505a74dfb878b71e #173
feat/additional-frontend-release a7383c573838f0f1ff11d655d543a9897036f22a #166
feat/controller-ssh-pairing ff4b84ff655f7d86f866c3c266d78dd3561e9120 #157
feat/native-readiness-probe 90c51088e61929e4814b103808b31c549d593168 #161
feat/react-frontend-p0 eebf657d07219bbe4368d5ab654812e6eb77e234 #132
feat/react-p1-backend-composition f1dc740bb337bb4cf2e4380affdca345f4b0e1b6 #134
feat/react-p1-host-isolation 85b5a367d7d36b3208c950b3e7c0b36a5a8bb1d3 #135
feat/react-p1-profile-selection 7b4474a0dc77a27844773eba4ba278894bdfe5fa #133
feat/react-p2-public-boundary 3c70f70c06864976736575c72802c7c00a5c8484 #136
feat/react-p4-openapi-metadata ea348bce0ffd51f6d2773b47cd7ea023a2795a84 #138
feat/react-p4-openapi-types 27e25c170e53eb3cd65919811ef1b58c6d4e45e1 #139
feat/react-p5-catalog 0a1c2f88143cf7a27a00609d4d3e3719939bfd5c #142
feat/react-p5-router-scaffold ada4e49bb4a62b16c11e231dddebc384d47477d7 #140
feat/react-p5-typed-transport f2f6e683450f5fa779cd24d247383ceb64e0b2a7 #141
feat/react-p6-playwright 1bbfb5b131ec15f2397d826b93c438a2e1f6b3a8 #144
feat/react-p6-public-ux c13a2c16c0d884048a298638601ab58754d60dac #143
feat/react-p7-acceptance-contract 6e5d6f2ba790ebc63d0ce346092e0a56c3ea3d7a #148
feat/react-p7-ci-isolation e91b42b7f25469a57c5a074cdd4fcc119d93181e #149
feat/react-p7-quality-validation b0b5153d20d84b6c38e46749946dad06e9e37857 #150
feat/react-p7-release-contract 76c1196815b50b0f1fbe313b1ecfaee398f1fe7a #147
feat/react-p7a-downstream-bootstrap 46654098844183f98a03ef15f021c5fb1d77c70c #151
feat/scoped-additional-app-setup 6bbc4e349a541f508256161184086b21a6b619e9 #169
feat/scoped-app-operations 5f0eeac138259eec1cc4fff893cc7386de045180 #174
feat/single-node-app-instance 4f30999056b758e5c4ef3a597f4201d293bf51fb #168
feat/sonarqube-on-demand-quality f8717708ddb1aecc2446ba3c8102c5142262f49d #178
fix/admin-seed-review b9bfc4ce4ff313c1c6b712cb0add7bd5de020403 #118
fix/ci-smoke-cleanup-status 4828bd7695f933169a3f029f934610d5c0da6854 #131
fix/p14-cloudflared-service-path 54c88f719cc0999391ebade124f2eadef56bbad1 #128
fix/p14-readiness-user-agent a4c2b22787bf3b665b8de355c94bf0649eac95e1 #129
fix/scoped-restart-compose-project f1e8d1d03c26e4cfec1e1a51ef61c58944582f34 #177
fix/single-node-configurable-fixtures b35c74cd6ca70f09656e6bd3ac84a9aa49635ea2 #160
fix/sonarqube-quality-review d60f54da62bd42072c3157e3e3bb0e66fb974829 #181
fix/trusted-operations-doc-descendants d1c7a6b0a3b46bc370432c5c7dc88318ef199b01 #175
security/remove-default-admin-seed 474cb095d84ac9ff0fae6a38505b972a88185fe3 #115
sync/portfolio-and-review-20261011 5e03e4243399329cbfa066cd5cd91ad630fc03f3 #154
update-dotnet-10 96c9117463454e23760ba4ea634956e1bad8ce84 #23
upgrade-p14-public-single-node ebd9f1971b9845536c482d6fdaca96f9d5879d76 #127

Template local branches deleted (name tip evidence):
docs/portfolio-execution-plan-20261011 63eb5b645fb3c8861e4ecc9a0b78dc615d9a5e19 table
docs/react-delivery-goal-refresh fecfe81fc45a754126a6bca345475613be7055dd table
docs/react-demo-native-node-handoff c2dfa725399972e3b6ceb5ee1966c3a0214fc3c0 table
docs/react-final-public-handover 31a3788a2d730af20d2d58a3a746d9a52b10b7d7 table
docs/react-node-readiness b82677338938e0f2e371d0304b7eeb3c38aed0e8 table
docs/react-p6-evidence ce3a3dd854e83b21b714e4b78ef2e37578b232d6 table
docs/react-p7a-node-handoff 91ea1283ed221fda65597f98c56364a0bd20be93 table
docs/react-single-repository-delivery c1a05258f652467fdbe16fde0adf2fa1122a3743 table
docs/record-admin-seed-plan 8022d390ba47d03e6490e4ead33dc5452f166e49 table
docs/sonarqube-baseline c6ad9481342d52d8f9bc689689be47c665f3a61f table
docs/sonarqube-closeout d293405e4555f62008af25e3c855e70b724814bb table
docs/sonarqube-on-demand-quality-20261011 213e607da260ea94da993cbd505a74dfb878b71e table
feat/additional-frontend-release a7383c573838f0f1ff11d655d543a9897036f22a table
feat/controller-ssh-pairing ff4b84ff655f7d86f866c3c266d78dd3561e9120 table
feat/native-readiness-probe 90c51088e61929e4814b103808b31c549d593168 table
feat/react-frontend-p0 eebf657d07219bbe4368d5ab654812e6eb77e234 table
feat/react-p1-backend-composition f1dc740bb337bb4cf2e4380affdca345f4b0e1b6 table
feat/react-p1-profile-selection 7b4474a0dc77a27844773eba4ba278894bdfe5fa table
feat/react-p2-public-boundary 3c70f70c06864976736575c72802c7c00a5c8484 table
feat/react-p4-openapi-metadata ea348bce0ffd51f6d2773b47cd7ea023a2795a84 table
feat/react-p4-openapi-types 27e25c170e53eb3cd65919811ef1b58c6d4e45e1 table
feat/react-p5-catalog 0a1c2f88143cf7a27a00609d4d3e3719939bfd5c table
feat/react-p5-router-scaffold ada4e49bb4a62b16c11e231dddebc384d47477d7 table
feat/react-p5-typed-transport f2f6e683450f5fa779cd24d247383ceb64e0b2a7 table
feat/react-p6-playwright 1bbfb5b131ec15f2397d826b93c438a2e1f6b3a8 table
feat/react-p6-public-ux c13a2c16c0d884048a298638601ab58754d60dac table
feat/react-p7-acceptance-contract 6e5d6f2ba790ebc63d0ce346092e0a56c3ea3d7a table
feat/react-p7-ci-isolation e91b42b7f25469a57c5a074cdd4fcc119d93181e table
feat/react-p7-quality-validation b0b5153d20d84b6c38e46749946dad06e9e37857 table
feat/react-p7-release-contract 76c1196815b50b0f1fbe313b1ecfaee398f1fe7a table
feat/react-p7a-downstream-bootstrap 46654098844183f98a03ef15f021c5fb1d77c70c table
feat/scoped-additional-app-setup 6bbc4e349a541f508256161184086b21a6b619e9 table
feat/scoped-app-operations 5f0eeac138259eec1cc4fff893cc7386de045180 table
feat/single-node-app-instance 4f30999056b758e5c4ef3a597f4201d293bf51fb table
feat/sonarqube-on-demand-quality f8717708ddb1aecc2446ba3c8102c5142262f49d table
fix/admin-seed-review b9bfc4ce4ff313c1c6b712cb0add7bd5de020403 table
fix/ci-smoke-cleanup-status 4828bd7695f933169a3f029f934610d5c0da6854 table
fix/clone-profile-test c50cff8fa0e24d25234012afd2263ea8d3f0b87c pr#216
fix/scoped-restart-compose-project f1e8d1d03c26e4cfec1e1a51ef61c58944582f34 table
fix/single-node-configurable-fixtures b35c74cd6ca70f09656e6bd3ac84a9aa49635ea2 table
fix/sonarqube-quality-review d60f54da62bd42072c3157e3e3bb0e66fb974829 table
fix/trusted-operations-doc-descendants d1c7a6b0a3b46bc370432c5c7dc88318ef199b01 table
security/remove-default-admin-seed 474cb095d84ac9ff0fae6a38505b972a88185fe3 table
update-dotnet-10 96c9117463454e23760ba4ea634956e1bad8ce84 table
fix/p14-cloudflared-service-path c84bf2177c4f4f33e932904d929506de4fd3ed42 ancestor-of-main
review/localsinglenode-senior-review 1bd71f73b151e68f1ab40720840704fba9261afa ancestor-of-main
upgrade/plan-main-pc-node-demo fba2df2a8779e7f97eb00850d3212a0c20f166d9 ancestor-of-main
HullImages 47fdfe754eb3c612c023bc9a608136471cc60042 ancestor-of-main
```
