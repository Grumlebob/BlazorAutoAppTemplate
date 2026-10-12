# Goal: Complete template cleanup

Goal prompt (under 3,500 characters):

```text
/goal Complete Plans/TemplateCleanupAndFeatureRetirement.md, P00–P24, and every exit criterion. Read the full plan, AGENTS.md, docs/Requirements.md, docs/FrontendProfiles.md and docs/Test.md first. Continue through implementation, validation, PRs, merges and origin/main verification; planning or local builds do not complete the goal.

Decisions fixed: retire demos and all three legacy Books redirects; add no legacy compatibility or route-absence checks. Test missing books at canonical `/books?bookId=99999999&bookMode=view`. Retain full Identity (passkeys, external/Google login, 2FA, recovery, email, personal data), both frontend profiles, all deployments, PostgreSQL/Redis/Data Protection, simulation, observability and quality tools.

Fetch origin/main. Inspect dirty state, worktrees, branches and PRs. Remove clean stale worktrees only after proving their commits merged or remain preserved; keep dirty/in-progress work. Retire unused Kilo tooling, state and owned worktrees; report anything command policy blocks. Use an isolated checkout if needed. Recheck consumers and evidence; do not repeat integrated work.

Execute bounded packets. Remove proven dead code, inputs and assets; simplify redundant branches and helper returns; correct seed docs; strengthen Redis fallback assertions; share pure deployment validators. Review and disposition every candidate. Preserve discovery/binding, intentional endpoint duplication, frontend hook symmetry, migrations, security, cancellation and caching. Warnings or low coverage alone do not prove dead code.

P13 removes demo routes, menus, HEAD aliases, traffic/simulation scenarios, NextDesignId and demo-only types/options. Preserve cover art, order and hover/focus motion. Repair E2E journeys, add retirement tests, update counts/docs and rebuild Tailwind. Blazor demo routes return 404; React keeps its SPA fallback. P14 removes old Books shims and moves missing-book E2E visits to canonical query route.

Implement P16's `--allow-insecure-localhost` / `-AllowInsecureLocalhost` contract across HTTP/browser paths; enforce target, loopback and redirect rules, warning and tests. Keep other traffic/write gates. Broader unchanged Identity coverage and replacing Caddy package verification remain separate work, not blockers or completed cleanup claims.

Run focused checks and full local gate before pushing code/configuration. Keep dotnet build/test sequential per checkout. Update strict test-count consumers in the same PR; never defer counts, lower them blindly or add skips. Commit generated CSS/schema; stage explicit paths. Require exact-head `build-test-push` before code merge and green exact-main CI. Markdown-only PRs use `[skip ci]`, full diff review, `git diff --check` and fetched origin/main verification without CI waits. Preserve protection.

No deployment, bootstrap, live-host mutation, global prune, volume deletion, lock reclamation, secret exposure, force-push or overwriting others' work. Use local/disposable fixtures. Resolve routine choices; ask only after a proven external hard stop and safe alternatives are exhausted. Complete required outcomes, dispositions and records. Verify integrated code, checks and docs on origin/main. Report PRs, SHAs, removals/retentions, validation and real limits.
```
