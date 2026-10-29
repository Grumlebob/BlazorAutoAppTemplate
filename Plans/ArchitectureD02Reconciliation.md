# D02: Final architecture reconciliation

Status: architecture guard and documentation reconciliation in progress; local validation and integration remain. Production deployment is outside this package.

## Verified prerequisites and scope

Selected main is `fe0339c25fe34f2920324bd7a335823817d67426`, the reviewed D01 squash from [PR 402](https://github.com/Grumlebob/GrumPlates/pull/402). Exact-head CI 40936686441 and exact-main CI 40940038966 passed, complete-content inclusion was verified, and the canonical helper accepted the final immutable payload receipt. D01 includes [A01 PR 398](https://github.com/Grumlebob/GrumPlates/pull/398), [A05 PR 400](https://github.com/Grumlebob/GrumPlates/pull/400) and the independently integrated import policy. Owning PRs retain detailed compatibility and local/profile/package evidence.

This package reconciles current documentation with the integrated Accounts, neutral React transport and component-owned modal lifecycle. It reviews the existing architecture scan, active legacy names, generated contract/endpoint/profile ownership and migration/publish/audit boundaries. The primary owns acceptance and integration. A bounded L1 inventory provides read-only supporting evidence; it cannot approve completion.

## Ownership map and accepted exceptions

The new architecture overview links the existing feature, frontend, account and testing guidance. Accounts documentation identifies current feature folders and shared contracts. Blazor documentation identifies the host/lifecycle split and its instance ownership. Existing React documentation already identifies the neutral factory/result helper and the Accounts-decorated private client; preserve that accurate description.

The three production managed assemblies remain Core, Server and Client; no extraction added another managed project. The server's Client reference is conditional on BlazorAuto. React generation remains metadata-only and uses the same server endpoint contract. Existing architecture and behavior suites must continue to cover those owners and both compositions.

Retain `ApplicationUser`'s existing CLR namespace `GrumPlates.Features.Login.Account`, with source under `Features/Accounts/Identity`, to avoid an unnecessary Identity/EF compatibility change. Retain historical migration designer strings and existing schema/history. Books' current-user and protected-endpoint integrations with Accounts are deliberate feature dependencies; neutral React transport does not absorb session decoration or private state. Keep middleware order, cache/owner/CSRF semantics and Data Protection/cookie identities unchanged.

## Verification and completion

Review the complete current architecture suite and finite active legacy-name search. Record actual coverage and any primary findings in this plan or the owning PR. Add source guards only for a demonstrated missing boundary; do not introduce arbitrary folder/line-count rules or duplicate behavior tests.

The complete L1 architecture inventory identified three production managed assemblies covered by the existing marker-based scans. Primary review found no guard preventing production source from returning to `Features/Login`, or another active type from using that legacy namespace. The added Accounts boundary tests protect those two specific outcomes across Core, Server and Client. Only the mapped `ApplicationUser` retains its precise legacy CLR name; its source must remain under Accounts/Identity. Historical migration designer strings are data, not runtime types, and remain unchanged. No general folder-count rule or runtime behavior change is introduced.

This is a mixed test/documentation PR. Run focused architecture feedback and the current full local gate, including both frontend profiles, React contract checks and the documentation-reading deployment audit. Review the complete diff and `git diff --check`, require green exact-head `build-test-push`, merge with the full reviewed head SHA and a non-skip squash message, then verify fetched complete content and successful exact-main CI with accepted provenance. Existing runtime compatibility and packaged acceptance evidence from the verified prerequisites remains relevant; required current gates still run.

Retain canonical evidence in the owning PR, archive unique notes with verified hashes, close verified-finished source resources and update Portfolio's primary-owned completion index. The earlier rejected Linux cleanup and other goal resources remain explicit dependencies until resolved; documentation delivery cannot silently complete the overall cross-project goal.
