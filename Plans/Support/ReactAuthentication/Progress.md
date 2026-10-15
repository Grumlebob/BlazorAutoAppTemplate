# React authentication foundation progress

## Current checkpoint

Status: planning/review handoff. Implementation remains paused until the owner invokes [ReactAuthenticationFoundationGoal.md](../../ReactAuthenticationFoundationGoal.md) or makes an equivalent implementation-and-verification request. The goal authorizes the stated work when invoked; do not ask for the same authorization again.

Read the latest [main plan](../../ReactAuthenticationFoundation.md) and [execution specification](ExecutionSpecification.md). The plan/specification are authoritative over the earlier draft. Begin with S00–S03, then follow the specification checklist. No implementation acceptance is passed yet.

### Preserved work

- Draft branch: `feat/react-authentication-foundation-20261015`; base `8599ffa527239a699f888c4aceea808f9829573a`. Locate the registered worktree with `git worktree list`.
- It contains uncommitted backend/React/configuration/Blazor transport changes. Preserve them for review/reuse; do not treat them as integrated or verified.
- Recovery patch in the primary checkout: ignored `Plans.local/ReactAuthenticationFoundation/DeferredImplementation-20261015.patch`, SHA-256 `DAC42AD1A33F1B5FBF3C956C4042A5DDAE181FCEC636A243E96F53CB6466B08A`. Already restored; do not apply twice. Its absence does not prevent clean implementation from tracked contracts.
- The earlier documentation plan was integrated by PR #307 as `e0150cef6d7d0be7253bca0542582379ba024264`. The PR introducing this review/specification/goal records its own exact integration evidence.
- Earlier draft compile/schema/typecheck/lint/build checkpoints are recorded in main plan §10. Later edits were not all rebuilt together. No authentication tests, real sign-in, real seed user, external mail or deployment has been performed.

## Reviewed recommendations to implement

Use the execution specification's final decisions: explicit client-config rather than 404 inference; focused handlers/forms; application-owned session state; server expected-user guards; read-only proof GETs; email-first registration; encrypted bounded database outbox; fresh locked proof/commit verification; enabled Blazor compatibility; unique normalized-email preflight; pinned offline password list; safe runtime settings/key persistence; mandatory real-cookie/TLS SMTP/browser/image verification.

No owner preference remains unresolved. Public SMTP/domain/provider inputs and actual deployment are later operational tasks, not prerequisites for template completion. Do not introduce paid services or live host mutations to satisfy local tests.

## Checkpoint ledger

Initial state for every row is pending. Replace grouped rows with exact checkpoint evidence as execution proceeds. A successful historical compilation must not change a row to passed.

| Checkpoints | State | Required evidence |
| --- | --- | --- |
| S00–S03 / A00 | Pending | Goal invocation, preserved-work manifest, source/tool baseline and real-cookie/TLS fixture proof |
| S04–S09 / A01 | Pending | Composition/contracts/policies/schema and guard failure tests |
| S10–S12 / A02 | Pending | Create-only/concurrent seed and env-secret isolation |
| S13–S17 / A03 | Pending | Real session/private CRUD, two users/Admin, races and Blazor transport |
| S18–S26 / A04 | Pending | Outbox/lifecycle/proof/management/email-first and frontend verification |
| S27–S30 / A05 | Pending | All target adapters, protected settings, durable keys and synthetic recovery |
| S31–S39 / A06 | Pending | Capability-aware acceptance, mandatory CI, image/browser/restore proof, docs/integration/cleanup |

For every checkpoint record: status, integrated or working source SHA, files, exact test/command names, sanitized evidence path/run URL, PR head/merge, exact-main CI, unresolved findings and next action. Record public conclusions without credentials, private host paths or token-bearing screenshots.

## Acceptance ledger

Every row below is pending. During execution give each individual ID its own evidence entry; a grouped range is not final acceptance.

| IDs | State | Focus |
| --- | --- | --- |
| AUTH01–AUTH09 | Pending | Disabled/public behavior, Admin seed, cookies/guards/abuse/ownership and cache isolation |
| AUTH10–AUTH18 | Pending | Email/proofs, revocation, deletion/export, metadata, profiles, keys and deployment settings |
| AUTH19–AUTH27 | Pending | Password/expiry, Blazor, races, capability discovery, transactional outbox and legacy migration safety |
| AUTH28–AUTH36 | Pending | Source/license/Unicode, safe errors, real fixtures, shared policy, recovery/adapter/image evidence, closeout and email-first security |

## Integration and closeout ledger

Implementation PRs: none. Implementation exact-head/main CI: not run. Implementation task checkout is intentionally retained for the owner's next chat. Do not remove it because the planning PR is merged.

After each implementation merge, record full PR-head and integrated SHAs, exact checks, content verification and deleted branch SHA. Once all useful draft content is integrated or explicitly reconciled, verify no process/resource/PR depends on the checkout, preserve required private evidence with SHA-256 and complete scoped cleanup. Keep the primary checkout and other sessions' work.

Use the documentation-only exception for final Progress-only updates. Record the last green code-main SHA and verify that final documentation commits do not change its code/configuration content. Keep final documentation integration/cleanup details in the PR description to avoid a self-referential commit loop.
