# Downstream clone readiness: workstream D goal

Complete workstream D (§ 10) of [DownstreamCloneReadiness.md](DownstreamCloneReadiness.md) end to end, then stop. Workstreams A–C are done; never redo them.

## Context

- Template: `C:/Users/jgrum/Documents/Programming/Csharp/BlazorAutoApp` (Grumlebob/BlazorAutoAppTemplate).
- Portfolio: `C:/Users/jgrum/Documents/Programming/Csharp/Portfolio` (Grumlebob/Portfolio).
- Read AGENTS.md, then the plan's § 3 and all of § 10, before acting. Follow procedures G (gate) and M (merge) exactly.
- The owner's 2026-10-14 decisions are in § 10. Do not ask about them again.

## Authority (owner, 2026-10-14)

Covered:

- branches, commits, pushes and PRs in both repositories;
- merging your own PRs: code PRs after a passing full gate and green exact-head `build-test-push`; docs-only PRs after the docs checks;
- deleting your own merged branches.

Not covered: deployments or workflow dispatches (CD, maintenance, readiness), node or SSH changes, Cloudflare, runners, repository settings, Dependabot PRs, `--admin` merges and force pushes.

## Steps

1. D0 preflight, at the start of every session.
2. D1: template fixture fix.
3. D2: Portfolio fixture fix.
4. D3: template CSP nonce.
5. D4: Portfolio plan cleanup and the Lighthouse decision.
6. D5: template guides, inventory rehearsal and mirror. Start it only after D1, D3 and D4 are merged.
7. D6: closeout.

D0 step 8 makes the run resumable: skip any step whose PR is already merged.

## Out of scope

- Do not start, plan, scaffold or design CarbonCalculator: no repository content, mockups, settings, runner, node setup, DNS or deployment.
- Only read `Plans.local/CarbonCalculator/`; never change it.
- Do not touch `ImprovedDb*`, `JDForecasting`, `KinoJoin`, `BlazorTusReliableUpload` or other sessions' work.

## Stop rules

- If the output differs from what a step expects, stop that step, record it in the D record, and continue with independent steps.
- If the same failure happens twice without an explained cause, stop that step and record it.
- If main CI is red at preflight, open no code PR in that repository.
- If a watcher stops, re-query the same run ID. Never re-push, re-run or dispatch because of it.
- Never weaken a test, the audit or CI to get a pass. Replace an audit rule only with a rule for the new behaviour.

## Done when

- The D1–D5 PRs are merged and verified on `origin/main`. Code PRs have green exact-head and main CI.
- Neither repository's local config has a `user.*` or `core.worktree` override, and the leak proof printed `NO-LEAK`.
- The plan's status says A–D are complete. The D record is filled with PRs, heads, merges, run IDs and skipped items, and the final record is in the D5 PR description.
- The D6 closeout passes: only the listed branches remain, and no D branch exists on origin.

Finally, report each PR with its merge SHA and CI run, anything skipped with its reason, and any finding that needs an owner decision.
