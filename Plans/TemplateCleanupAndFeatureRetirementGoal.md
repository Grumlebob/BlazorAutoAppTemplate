# Goal: Complete template cleanup

Goal prompt (under 3,500 characters):

```text
/goal Complete Plans/TemplateCleanupAndFeatureRetirement.md, P00–P24, and every exit criterion. Read full plan, AGENTS.md, docs/Requirements.md, docs/FrontendProfiles.md and docs/Test.md. Finish implementation, checks, PRs, merges and origin/main verification; local work alone does not complete goal.

Fixed decisions: retire design demos and all three legacy Books redirects. Add no legacy compatibility or route-absence tests. Test missing books at `/books?bookId=99999999&bookMode=view`. Retain full Identity, both frontend profiles, all deployments, PostgreSQL/Redis/Data Protection, observability and quality tools. Retire the rare simulator fully: code, tests, scripts, active docs, CI/config hooks and four obsolete simulator plans. Keep telemetry, dashboards, alerts and concise retirement evidence here/backlog. Add no simulator-absence tests.

Fetch origin/main. Inspect dirty state, worktrees, branches and PRs. Remove stale worktrees only after proving commits merged or preserved; keep dirty work. Ignore user-local Kilo data; it is outside this cleanup and requires no action. Do not repeat integrated work or overwrite others' changes.

Execute bounded packets. Remove proven dead code, inputs and assets; simplify redundant branches/helpers; correct seed docs; strengthen Redis fallback assertions; share pure deployment validators. Review every candidate. Preserve binding/discovery, intentional endpoint duplication, frontend hook symmetry, migrations, security, cancellation and caching. Warnings alone do not prove dead code.

P13 removes demo routes, menus, HEAD aliases, traffic scenarios, NextDesignId and demo-only types/options. Preserve cover art, order and hover/focus motion. Repair journeys, update counts/docs and rebuild Tailwind. Keep React SPA fallback. P14 removes old Books shims and moves missing-book E2E visits to canonical query route. P16 removes simulator code, tests, wrappers, CI/config references and recalculates exact .NET test counts. P17 removes active guidance and closes Q-001/Q-008; P22 deletes four obsolete simulator plans and keeps observability guidance plus concise retirement evidence.

Run focused checks and full local gate before pushing code/config. Keep dotnet build/test sequential per checkout. Update exact test-count consumers in same PR; never guess, defer, weaken or add skips. Stage explicit paths. Require green exact-head `build-test-push` before code merge and exact-main CI after. Markdown-only PRs use `[skip ci]`, full diff review, `git diff --check`, then fetch and verify `origin/main` without waiting for CI. Preserve branch protection.

No deployment, bootstrap, live-host mutation, global prune, volume deletion, lock reclamation, secret exposure, force-push or overwriting others' work. Use local/disposable fixtures. Resolve routine choices; ask only for a proven external hard stop after safe alternatives fail. Complete dispositions and records. Verify integrated code, checks and docs on `origin/main`. Report PRs, SHAs, removals, validation and real limits.
```
