# React authentication foundation progress

## Current checkpoint

Status: active implementation. The owner activated [ReactAuthenticationFoundationGoal.md](../../ReactAuthenticationFoundationGoal.md) on 2026-10-15, authorizing implementation, isolated verification and gated PR integration. Live deployments, shared-host changes and external messages remain outside scope.

The latest [main plan](../../ReactAuthenticationFoundation.md), [execution specification](ExecutionSpecification.md) and AGENTS.md were read at `1236efdae411d3e2f5c8c531eb5dda2a27457ffc`. The plan/specification are authoritative over the earlier draft. A00 (S00–S03) is integrated by PR #309 as `2fa8b51107923521a62f54b721896c06c7979a60`; its exact-main CI is green. A01 is active locally. No complete AUTH acceptance row is passed yet.

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
| S00 / A00 | Verified on main | Goal activation and current contracts read at `1236efdae411d3e2f5c8c531eb5dda2a27457ffc`; no additional implementation approval required; PR #309 integration evidence below |
| S01 / A00 | Verified on main | Preserved tracked/untracked SHA-256 manifest and ignored-file inventory in task-local `Plans.local/ReactAuthenticationFoundation/ResumeManifest-20261015.json` and `ResumeStatus-20261015.txt`; recovery patch hash verified, not reapplied |
| S02 / A00 | Verified on main | Fast-forwarded draft from `8599ffa527239a699f888c4aceea808f9829573a` to `1236efdae411d3e2f5c8c531eb5dda2a27457ffc` without changing draft files; current gate read in `docs/Test.md`; SDK 10.0.303, Node 24.21.0, Docker 29.8.2; WSL supplies Linux .NET, Docker, Python 3.12.3 and ShellCheck |
| S03 / A00 | Verified on main | `AccountFixtureTests`: five tests passed in both complete profile suites; anonymous/fake-header denial, trusted STARTTLS MIME capture, untrusted/unrelated-CA rejection and plaintext refusal. Task-local evidence `Plans.local/ReactAuthenticationFoundation/A00Gate/frontend-profiles/{BlazorAuto,React}/suite.trx`. Actual sign-in proof is in the local S07 work; full production sign-in acceptance remains S13 and packaged-browser HTTPS remains S33. |
| S04 / A01 | In progress, uncommitted | Extracted session/login/logout into `Session/AccountSessionOperations.cs`; focused lifecycle operations and replacement of module-global React state remain required |
| S05 / A01 | Implemented locally; packet gate pending | Immutable startup `AccountOptions` and app identity; `/api/client-config` describes disabled/enabled capability without cookies or secrets. `AccountOptionsTests` and `ClientConfigurationTests` cover reload isolation, incomplete/unsafe settings, safe errors, stable identity and both runtime modes. Seed policy is checked before database access. |
| S06 / A01 | In progress, uncommitted | Metadata-only generation includes capability and session services; `npm run api:generate`, React typecheck and lint pass. Lifecycle DTOs/statuses/errors still need the final contracts. |
| S07 / A01 | In progress, uncommitted | Shared Unicode validator, exact pinned common-password resource/hash/MIT attribution, 256-unit DTO bounds and fixed cookie/stamp settings implemented. `AccountPasswordTests` and `AccountCookieTests` prove scalar boundaries, legacy hash verification, actual Identity cookies, role refresh without extending 8-hour/14-day expiry and stamp revocation across two cookie jars. Enabled Blazor UI policy and complete failure/lockout acceptance remain pending. |
| S08 / A01 | Pending | Unique-email preflight/migration, outbox and PostgreSQL key-store schema; clean/refusing upgrade and both profile bundles |
| S09 / A01 | In progress, uncommitted | Endpoint-tagged expected-user middleware rejects missing/mismatched/duplicate owners before private use cases and preserves unknown API 404s. `AccountGuardTests` prove real-cookie read/write/logout races, no owner-ID disclosure, CSRF rejection and no rejected-write effects. Early bounded body handling, complete guard ordering, distinct account-write limit and retained Blazor transport remain required. |
| S10–S12 / A02 | Pending | Create-only/concurrent seed and env-secret isolation |
| S13–S17 / A03 | Pending | Real session/private CRUD, two users/Admin, races and Blazor transport |
| S18–S26 / A04 | Pending | Outbox/lifecycle/proof/management/email-first and frontend verification |
| S27–S30 / A05 | Pending | All target adapters, protected settings, durable keys and synthetic recovery |
| S31–S39 / A06 | Pending | Capability-aware acceptance, mandatory CI, image/browser/restore proof, docs/integration/cleanup |

For every checkpoint record: status, integrated or working source SHA, files, exact test/command names, sanitized evidence path/run URL, PR head/merge, exact-main CI, unresolved findings and next action. Record public conclusions without credentials, private host paths or token-bearing screenshots.

### Recovery and current findings

The task checkout contains the original draft plus this goal's changes. Process inspection found no .NET application/build/test process attached to it before resumption; existing .NET processes were editor build hosts. No repository `StartAgentTask.ps1` or `GetAgentStatus.ps1` exists, so the machine-specific binding workflow is inapplicable here. This active goal owns the retained authentication checkout; other task checkouts remain untouched.

Review confirms that the draft's synchronous mail, password-first registration, module-global React session state require replacement; both frontend transports must now participate in the new expected-user guard. The old backend password policy has been replaced locally; both frontend policies still need reconciliation. Earlier generated contracts and compilation are not acceptance evidence. The A00 snapshot introduces verification support only; none of the preserved draft runtime is included. Next: complete S04–S09 with their failure tests before integrating A01.

A01 source is based on local merge `add6c6172383a018c9999ae0b4aa7d34eeeae6e8`, which reconciles PR #309 without overwriting the preserved draft. Targeted BlazorAuto account/architecture tests passed 72/72 with zero warnings in `TestResults/account-foundation-blazor.trx`. React account tests passed 59/59, and later guard/password/architecture tests passed 32/32 with zero warnings in `TestResults/account-guards-react.trx`. After correcting the draft's DTO placement to `BlazorAutoApp.Core/Features/Login/UseCases/Shared`, the broader React backend suite passed 243 tests with 13 expected opt-in skips in `TestResults/react-working-suite.trx`; that broader run preceded the additional guard tests. React unit tests passed 31/31; typecheck, lint, metadata generation and focused .NET format verification passed. These local results do not replace A01's eventual complete local gate, browser/image acceptance or exact-head/main CI.

OpenAPI generation contacts neither database nor SMTP. Resource bytes were downloaded once from the specified SecLists commit and matched SHA-256 `68782d6a4a19a4768d5f15dd66bd534e7a33055cc755411e33f16d18c50fdcce`; `.gitattributes` preserves their bytes on all platforms. The framework's non-sliding stamp renewal preserved absolute expiry in real-cookie tests, so the draft's custom principal-validation wrapper was removed. This is a verified implementation choice, not a custom cryptographic/session validator. Password DTOs preserve whitespace, including a valid all-space candidate, while refusing empty values; validation never trims password contents.

## Acceptance ledger

Every row below is pending. During execution give each individual ID its own evidence entry; a grouped range is not final acceptance.

| IDs | State | Focus |
| --- | --- | --- |
| AUTH01–AUTH09 | Pending | Disabled/public behavior, Admin seed, cookies/guards/abuse/ownership and cache isolation |
| AUTH10–AUTH18 | Pending | Email/proofs, revocation, deletion/export, metadata, profiles, keys and deployment settings |
| AUTH19–AUTH27 | Pending | Password/expiry, Blazor, races, capability discovery, transactional outbox and legacy migration safety |
| AUTH28–AUTH36 | Pending | Source/license/Unicode, safe errors, real fixtures, shared policy, recovery/adapter/image evidence, closeout and email-first security |

## Integration and closeout ledger

Implementation PR [#309](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/309): head `fd81e7a18dbaed44c700e02a5098e99cc384634e`, squash merge `2fa8b51107923521a62f54b721896c06c7979a60`. Required exact-head `build-test-push` and CodeQL passed in [CI run 38778975039](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38778975039). All seven integrated paths match the PR head. Exact-main [CI run 38780158049](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38780158049) passed both `validate` and `build-test-push` for that exact merge SHA. The last green code-main SHA is `2fa8b51107923521a62f54b721896c06c7979a60`; subsequent Progress-only closeout uses the documentation exception, with final documentation-main evidence in its PR description.

The A00 local gate passed on a clean clone of its exact head: BlazorAuto 197 passed/13 expected opt-in skips; React 189 passed/13 expected opt-in skips. The new five-test fixture suite was not skipped. All other `docs/Test.md` gate commands passed. Docker Desktop could not bind the WSL temporary checkout for actionlint; the pinned actionlint image passed with a Windows bind mount after verifying the workflow/configuration content matched the exact head. Packaged React image `sha256:2b948da3c382cd72374d9f0ed712d7927d216a8ef5357a877810cceb2a692058` passed disabled HTTP acceptance, including private anonymous denial, absent account routes and no public cookies. The explicit packaged React Playwright test passed 1/1 with zero skips. The current React smoke script itself only runs HTTP checks, so a task-local harness invoked the existing browser test before its normal scoped cleanup. This is disabled-mode baseline evidence, not enabled account acceptance. The NuGet transitive advisory query found no known vulnerable dependencies at verification time.

The authentication task checkout is retained and owned by this active goal: it contains unmerged A01 work and the preserved lifecycle/React draft. A00's disposable verification clones and exact test image were removed after inspecting tracked/untracked/ignored files and live process/resource dependencies. Its evidence archive is outside the task checkout in ignored primary-checkout storage, SHA-256 `EDCEC42E9896921DE74DBD4ADC8BCC0B974750DF248F4DD5A09EC7DFF04C44C3`; reproducible outputs were not archived. The finished packet branch `test/auth-fixtures-a00-20261015` is reconciled at full SHA `fd81e7a18dbaed44c700e02a5098e99cc384634e`; deletion verification is recorded in PR #309. Other sessions' checkouts remain untouched.

After each implementation merge, record full PR-head and integrated SHAs, exact checks, content verification and deleted branch SHA. Once all useful draft content is integrated or explicitly reconciled, verify no process/resource/PR depends on the checkout, preserve required private evidence with SHA-256 and complete scoped cleanup. Keep the primary checkout and other sessions' work.

Use the documentation-only exception for final Progress-only updates. Record the last green code-main SHA and verify that final documentation commits do not change its code/configuration content. Keep final documentation integration/cleanup details in the PR description to avoid a self-referential commit loop.
