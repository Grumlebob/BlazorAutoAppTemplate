# React authentication foundation progress

## Current checkpoint

Status: active implementation. The owner activated [ReactAuthenticationFoundationGoal.md](../../ReactAuthenticationFoundationGoal.md) on 2026-10-15, authorizing implementation, isolated verification and gated PR integration. Live deployments, shared-host changes and external messages remain outside scope.

The latest [main plan](../../ReactAuthenticationFoundation.md), [execution specification](ExecutionSpecification.md) and AGENTS.md were read at `1236efdae411d3e2f5c8c531eb5dda2a27457ffc`. The plan/specification are authoritative over the earlier draft. S00–S03 recovery and fixture readiness are complete locally; integration gates are pending. No implementation acceptance is passed yet.

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
| S00 / A00 | Complete locally; integration pending | Goal activation and current contracts read at `1236efdae411d3e2f5c8c531eb5dda2a27457ffc`; no additional implementation approval required |
| S01 / A00 | Complete locally; integration pending | Preserved tracked/untracked SHA-256 manifest and ignored-file inventory in task-local `Plans.local/ReactAuthenticationFoundation/ResumeManifest-20261015.json` and `ResumeStatus-20261015.txt`; recovery patch hash verified, not reapplied |
| S02 / A00 | Complete locally; integration pending | Fast-forwarded draft from `8599ffa527239a699f888c4aceea808f9829573a` to `1236efdae411d3e2f5c8c531eb5dda2a27457ffc` without changing draft files; current gate read in `docs/Test.md`; SDK 10.0.303, Node 24.21.0, Docker 29.8.2; WSL supplies Linux .NET, Docker, Python 3.12.3 and ShellCheck |
| S03 / A00 | Complete locally; integration pending | `AccountFixtureTests`: 5 passed under React, zero warnings; anonymous/fake-header denial, trusted STARTTLS MIME capture, untrusted/unrelated-CA rejection and plaintext refusal. Command: `dotnet test BlazorAutoApp.Test/BlazorAutoApp.Test.csproj -p:FrontendProfile=React --filter FullyQualifiedName~AccountFixtureTests`; task-local evidence `Plans.local/ReactAuthenticationFoundation/TestResults/account-fixtures-react.trx`. Real-cookie login remains S13; packaged-browser HTTPS remains S33. |
| S04–S09 / A01 | Pending | Composition/contracts/policies/schema and guard failure tests |
| S10–S12 / A02 | Pending | Create-only/concurrent seed and env-secret isolation |
| S13–S17 / A03 | Pending | Real session/private CRUD, two users/Admin, races and Blazor transport |
| S18–S26 / A04 | Pending | Outbox/lifecycle/proof/management/email-first and frontend verification |
| S27–S30 / A05 | Pending | All target adapters, protected settings, durable keys and synthetic recovery |
| S31–S39 / A06 | Pending | Capability-aware acceptance, mandatory CI, image/browser/restore proof, docs/integration/cleanup |

For every checkpoint record: status, integrated or working source SHA, files, exact test/command names, sanitized evidence path/run URL, PR head/merge, exact-main CI, unresolved findings and next action. Record public conclusions without credentials, private host paths or token-bearing screenshots.

### Recovery and current findings

The task checkout contains the original draft plus this goal's changes. Process inspection found no .NET application/build/test process attached to it before resumption; existing .NET processes were editor build hosts. No repository `StartAgentTask.ps1` or `GetAgentStatus.ps1` exists, so the machine-specific binding workflow is inapplicable here. This active goal owns the retained authentication checkout; other task checkouts remain untouched.

Review confirms that the draft's synchronous mail, password-first registration, module-global React session state, missing expected-user guards and old password policy require replacement. Earlier generated contracts and compilation are not acceptance evidence. Changes remain local until a coherent packet passes the full gate. Next: validate A00's isolated committed snapshot with both profiles and the full local gate, then implement S04–S09 with their failure tests. The A00 snapshot introduces verification support only; none of the preserved draft runtime is included.

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
