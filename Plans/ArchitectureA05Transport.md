# A05: React transport ownership

Status: implementation in progress. This package follows verified Accounts integration and preserves existing transport behavior.

## Baseline and prerequisite

Selected source: main `0988e75c35c62138d88ab762a5fcbca8589147e6`. Accounts [PR398](https://github.com/Grumlebob/GrumPlates/pull/398) is verified integrated, including successful exact-main [CI40725051996](https://github.com/Grumlebob/GrumPlates/actions/runs/40725051996). Its React suite passed75 tests, and its packaged account/private-book journeys passed without skips. The reviewed account and public transport files are unchanged between that tested source and this selected main.

Read current AGENTS, testing, requirements and React guidance. Reviewed current worktrees, claims and open PRs; this isolated task owns only the transport paths below. Independent C# import cleanup retains its existing owner. No production deployment or provider request is part of this package.

## Ownership map and primary design

| Current responsibility | Resulting owner |
| --- | --- |
| AccountApi generated CRUD type and createAccountApi factory in features/accounts/account-api.ts | Neutral ApiClient/createApiClient in app/api/api-client.ts; each caller explicitly selects credentials and fetch implementation |
| Generic apiResult normalization in features/accounts/account-api.ts | app/api/api-result.ts, with its existing response/error behavior preserved |
| Session/configuration DTO aliases, disabled session, AccountChangedError and safe return path | Remain under features/accounts/account-api.ts |
| Public author-book operations and strict text/JSON response handling | Remain in app/api/client.ts; use the neutral factory with credentials omitted as before |
| Private client decoration and lifetime | Remain in AccountSessionController; its single client uses same-origin credentials and keeps existing middleware and method guards |
| Account forms, private books and routes | Use the generic result helper while retaining the provider's decorated accounts.api instance |

Generic modules import no Accounts module. The controller still owns captured-user headers, CSRF refresh, cancellation, parsing-time generation checks, account-change signaling and private-cache clearing. The provider/context still exposes the controller's guarded methods; moving the type does not create another private client.

Keep public credentials omitted and the current public wrapper's stricter JSON handling. Keep private bodyless204 support, missing-success-data rejection, malformed-body failures, safe HTTP/network errors and cancellation semantics. Account export continues through the guarded typed operation before creating its local JSON Blob. No existing raw/binary response API was found; this move introduces no new transport capability.

The L1 inventory and primary source review cover every AccountApi/createAccountApi/apiResult consumer. Mechanical import updates may be delegated within an explicit allowlist; the primary owns factory/controller changes, security-sensitive review, response coverage, validation and integration.

## Verification and completion

Reuse public transport/error tests, account controller/provider/draft/form cases and catalog/detail behavior. Existing controller cases cover isolated owners/CSRF, refresh races, disposal, owner changes during response parsing, same-owner refresh, unavailable sessions, application identity changes and expiry. Add focused response characterization only for uncovered malformed/missing success bodies; retain current behavior.

Before push, compare extracted bodies and the controller's remaining body with the selected baseline, inspect every import and confirm the single decorated private instance. Run the React contract/typecheck/lint/tests/build and the current full repository local gate sequentially, then isolated packaged account/private-book acceptance. Required cases must run without skips. Record selected/passed/failed/skipped counts in the owning PR.

Completion requires green exact-head build-test-push, reviewed squash integration, fetched full-content inclusion and successful required exact-main CI. Then archive unique evidence and close only this task's resources. D01 becomes eligible after this package is verified integrated.
