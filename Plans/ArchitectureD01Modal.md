# D01: Book modal operation lifecycle

Status: inventory and primary design reviewed; implementation and validation remain in progress. Production deployment is outside this package.

## Baseline and ownership

Selected main: `9a7177dec56abaa1a665c4bb481d5dd35b377c6a`. Accounts [PR 398](https://github.com/Grumlebob/GrumPlates/pull/398) and transport [PR 400](https://github.com/Grumlebob/GrumPlates/pull/400) are verified integrated. Exact-main [CI 40835101319](https://github.com/Grumlebob/GrumPlates/actions/runs/40835101319) passed validation and publication. Read current AGENTS, testing, requirements, browser guidance, modal/route/editor/bookcase implementations and existing client/browser tests. Refreshed worktrees, claims and open PRs before creating the isolated task.

The modal component has not changed since the integrated template rename. Existing A05 baseline reports at `0794aba065b50259ea877f0655e4616d9709b111` execute all ten BookModalRouteStateTests and UserBookcaseStateTests cases successfully, without skips. Current main repeats the complete profile gate successfully. Between that tested source and selected main, the relevant book implementations change only independent imports; modal, route and operation bodies remain unchanged. These tests establish route parsing, stale bookcase loads, requested delete identity and cancelled-delete behavior. Browser acceptance of the resulting modal remains required.

This task owns `GrumPlates.Client/Features/Books/BookModal/BookModalHost.razor`, new `BookModalLifecycle.cs` in that folder, new `GrumPlates.Test/Features/Books/Client/BookModalLifecycleTests.cs`, new `GrumPlates.Test/E2E/Features/Books/BookModalNavigationE2ETests.cs`, and this plan. The independent C# cleanup task retains its policy/import claims and current validation turn. No shared DI registration, API contract, cookie, data model, route parser, UserBookcaseState or editor validation behavior changes are planned.

## Before/after ownership and design

| Responsibility in BookModalHost | Resulting owner |
| --- | --- |
| Location subscription, URI parsing, focus scheduling, keyboard Escape, rendering and component disposal | Remain explicit in BookModalHost |
| Parsed request, displayed book, editor instance/request key, loading/save/delete/error/confirmation state | One component-owned BookModalLifecycle instance |
| Load generations, cancellation sources, operation identity and late-result rejection | BookModalLifecycle alone, with original cancellation/disposal timing |
| Author/user source selection, authentication wait, create/edit/delete request composition and cache application | BookModalLifecycle, reusing the same APIs and UserBookcaseState |
| Navigation side effects | Lifecycle emits its existing navigation intent through one callback owned by the component; callback executes synchronously at the existing guarded completion point |
| Shared bookcase contents and versioning | Existing UserBookcaseState remains the sole owner; lifecycle calls its existing methods |

The component constructs and disposes the lifecycle rather than registering a scoped or singleton service. Prerender and interactive component instances keep independent state as before. The component supplies its current cascading authentication task for each load. The lifecycle exposes read-only state properties and explicit operations, with a Changed event for the component's renderer dispatch. It exposes no cancellation source or mutable context bag. EditorModel remains the existing form model; editor identity follows the unchanged EditorRequestKey.

Preserve every existing route and error message, create/update normalization, user/author distinction, authentication redirect, cancellation boundary, and cache-update order. Navigation must remain inside the current-operation guard; deferring it until a separate asynchronous result continuation could close a newer modal. Keep the original component logging category, structured message and URI context. Complete each cancellation source only when its owning asynchronous operation finishes; disposal cancels outstanding work and does not allocate another synchronization owner.

## Verification and completion

Reuse route-state, bookcase, ownership/transport and BooksE2ETests. Add only missing observable lifecycle cases: an older load completing after a newer request, navigation superseding an in-flight save/delete, and completion after disposal. Use controlled task completions and the public lifecycle actions; do not assert private field shapes or passive DTO construction. A browser case also exercises rapid normal Blazor navigation between two seeded public author books, then verifies the latest modal, focus and Escape close. This case needs no API interception, renderer override or renderer-dependent skip.

After extraction, review the complete diff and compare request composition, operation checks, messages and unchanged markup/classes. Run focused client/transport feedback before the complete current local gate, both frontend profiles and affected isolated Blazor browser journeys. Required create/view/edit/delete/close, keyboard focus and rapid-navigation cases must execute without skips. Regenerate Tailwind only if class discovery/output changes; preserve the generated output when unchanged. Keep build/test and machine-heavy work sequential under the current capacity reservation.

Completion requires successful exact-head build-test-push, primary review, squash integration with a non-skipping message, fetched full-content inclusion and successful exact-main CI. Archive unique evidence and close only verified-finished resources. D02 remains a separate final reconciliation package.
