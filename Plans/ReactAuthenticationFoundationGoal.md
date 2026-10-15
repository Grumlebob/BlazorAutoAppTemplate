# React authentication foundation goal

Complete and verify the template authentication foundation defined by Plans/ReactAuthenticationFoundation.md and Plans/Support/ReactAuthentication/ExecutionSpecification.md, including all reviewed recommendations. Finish S00-S39 and AUTH01-AUTH36. Work in BlazorAutoAppTemplate; CarbonCalculator work waits until a later request.

## Start

Invoking `/goal Plans/ReactAuthenticationFoundationGoal.md` authorizes implementation, tests, browser/image/SMTP-fixture verification and gated PR integration. This lifts the earlier pause. Live deployment, shared-host changes, external messages, paid services and real account provisioning are not authorized.

Read AGENTS.md and the latest origin/main versions of the plan, execution specification and Plans/Support/ReactAuthentication/Progress.md before using the old checkout. Follow section 10 of the plan to preserve/resume the draft on feat/react-authentication-foundation-20261015. Inspect tracked/untracked/ignored edits, processes and ownership. Verify the recovery patch hash if needed; never apply it twice. If private artifacts are unavailable, implement from tracked contracts. Do not overwrite others' work or restart useful completed work.

## Execute

Follow the numbered checkpoints and evidence. Deliver Identity app cookies, explicit capability discovery, email/password sessions, optional create-once environment-configured Admin, CSRF/expected-user guards, private Books CRUD, safe account lifecycle, email-first registration and encrypted bounded mail outbox. Preserve public-disabled mode and enabled/legacy Blazor compatibility. Exclude MFA, passkeys, external login and SSO additions.

Finish optional settings/secret propagation and key persistence through all retained deployment targets. Keep secrets out of source, Vite, logs and public artifacts. Verify real cookies, two users/Admin, token/session races, TLS SMTP, worker failures, restart/isolated restore and packaged React in both modes. Fixtures use isolated resources and generated credentials; no production SMTP account, DNS or live node is needed.

Use sound free dependencies, framework cryptography and the selected defaults. Resolve routine technical choices autonomously and record material decisions; do not reopen settled scope. Fix findings rather than silently deferring requirements or weakening checks. Progress independent work around genuine external blockers; record exact evidence and the smallest missing input.

## Finish

Keep Progress current after each checkpoint: source, changed paths, tests/evidence, PR/head/merge/main CI and next action. Run the full current local gate plus explicit auth browser/image checks before code push; keep dotnet build/test sequential. Use explicit staging and small coherent PRs. Require green build-test-push on each exact code PR head, then green exact-main CI and integrated-content verification. Use AGENTS.md's docs-only exception for progress-only closeout and its cleanup rules.

Complete only when every checkpoint and acceptance row has final evidence, docs/runbooks and migration/deployment contracts agree, no required fix remains unmerged, and finished task resources/checkouts/branches are reconciled. Preserve private inputs and other sessions. Report integrated commits, verification, limitations and later deployment-only inputs.
