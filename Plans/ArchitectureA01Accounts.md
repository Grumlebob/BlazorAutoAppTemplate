# A01: GrumPlates Accounts boundary

Status: In progress. Source and move map reviewed before implementation on 2026-10-28.

This task implements GP:A01 from Portfolio's CrossProjectArchitectureUpgrade plan. Production deployment is outside scope. A05, D01 and D02 follow only after their prerequisites integrate.

## Baseline and ownership

- Source: `origin/main` and task input `9cb1961f8959b3e7bf7a8b30f37320ed2bb03cef`.
- Task branch: `task/architecture-a01-accounts-20261028`. Primary session: `01a181f1-01d8-70b3-8b14-5f4dba6503cf`.
- Main was clean and had no other registered worktrees. The only open PR was unrelated dependency PR #390. The historical report-retention claim refers to an absent checkout and already integrated work; preserve its record.
- Read current AGENTS.md, docs/Test.md, docs/Requirements.md, docs/Accounts.md, browser and infrastructure testing guidance, frontend composition, project profile wiring, migration snapshot and account behavior tests.
- Own the source moves below and all imports, Razor references, profile/resource wiring, account test filters, matching audit assertions, current documentation links, and this plan. Keep historical migrations and historical plans unchanged.
- Luna L1 independently checked the pinned reference inventory. The primary reviewed the inventory against source and accepted the finite map below. The worker made no edits and ran no builds or tests.

## Compatibility baseline

The exact source's current CI validation job completed before edits. Reuse that fresh execution rather than duplicate the same baseline while another session holds machine-heavy capacity: [run 40663362881, validate job 122731727582](https://github.com/Grumlebob/GrumPlates/actions/runs/40663362881/job/122731727582). The completed job log was read through the job-logs API and retained in ignored task scratch.

`bash Scripts/CI/validate-frontend-profiles.sh <results-directory>` on the pinned SHA produced:

| Suite | Passed | Failed | Expected opt-in skips | Selected |
| --- | ---: | ---: | ---: | ---: |
| BlazorAuto non-account | 196 | 0 | 15 | 211 |
| BlazorAuto accounts | 150 | 0 | 0 | 150 |
| React non-account | 188 | 0 | 15 | 203 |
| React accounts | 136 | 0 | 0 | 136 |

The account suites cover fresh/duplicate-email migration behavior, cookies/stamps, request guards, registration/recovery, mail/outbox, export/deletion, private Books ownership, Data Protection, Blazor adapters and external-account compatibility. Browser opt-ins are not claimed as exercised by these ordinary suites. Required affected browser/package acceptance remains to run.

## Boundary and compatibility decisions

- Account registration moves to `Accounts/DependencyInjection.cs`; middleware moves to `Accounts/AccountApplicationBuilderExtensions.cs`. Retain method bodies, call order, registration lifetimes, options and enabling conditions. Identity backend registration remains separately owned by `Accounts/Identity`.
- Existing `AccountOperations` and handlers retain operations, DbContext/transaction boundaries and synchronization. No new collaborators or mutable state owners are introduced by this mechanical move.
- Blazor components, redirect/revalidation/current-user adapters, passkey form models and local/demo seed live under `Accounts/Blazor`. Backend Identity configuration, no-op mail fallback and HTTP-principal identity access live under `Accounts/Identity`.
- `ApplicationUser` moves physically to Identity but retains exactly `GrumPlates.Features.Login.Account.ApplicationUser`. Active consumers use explicit type aliases where needed. This is the sole active legacy CLR type exception; do not rename its model identity or historical migration metadata.
- `AccountOutboxMessage` moves to the new Accounts namespace. Only that type's current snapshot CLR metadata follows the move. Preserve relational mapping, migration IDs, history, schema and historical designers; require migration/pending-model evidence before integration.
- Preserve `GrumPlates.Accounts.CommonPasswords`, resource bytes/hash and license output. Update `.gitattributes` with the resource path. Update React profile compile exclusions with the Blazor paths.
- Update the explicit PasskeySubmit JavaScript asset lookup with its source move; verify emitted asset resolution and browser behavior. Keep account route strings and form contracts unchanged.
- Move all account tests to Accounts, including local-seed and identity-accessor tests. Update both positive/negative profile filters and their tests/audit assertions so the account partition remains explicit and cannot silently skip.
- Keep Core contracts free of HTTP/Identity implementations. Preserve DTO names, JSON fields, API schemas, cookies, CSRF headers, Data Protection purposes and persisted formats.
- Tailwind automatically scans source directories. Compare rebuilt CSS after the move; do not change class markup.

## Verification and integration still required

- Review complete rename-aware diff, legacy references (classify user aliases, current snapshot and historical records), resource bytes, Razor imports, composition bodies and relational metadata.
- Run focused feedback plus every current local gate command in docs/Test.md, including both frontend profiles, React contract/package checks and updated audit/test-filter checks. Serialize heavy builds/tests with other sessions.
- Run isolated packaged/browser account smoke for both profiles, including moved passkey asset resolution. Ordinary browser opt-in skips are not acceptance proof.
- Require exact-head `build-test-push`, primary review and squash merge with the full head SHA; fetch and verify integrated content and exact-main CI. Record the canonical evidence in the PR, then update Portfolio's index.
- Archive unique evidence, record branch SHA, release the task claim, and remove only verified-finished owned resources.

## Before/after file ownership map

The following map was fixed before source mutation. Middleware is additionally split from the mapped DependencyInjection file as described above. Referencing consumers retain their current owners.

| Before | After |
| --- | --- |
| `GrumPlates.Client/Features/Login/Components/RedirectToLogin.razor` | `GrumPlates.Client/Features/Accounts/Components/RedirectToLogin.razor` |
| `GrumPlates.Core/Features/Login/UseCases/Shared/AccountContracts.cs` | `GrumPlates.Core/Features/Accounts/Contracts/AccountContracts.cs` |
| `GrumPlates.Test/E2E/Features/Login/IdentityE2ETests.cs` | `GrumPlates.Test/E2E/Features/Accounts/IdentityE2ETests.cs` |
| `GrumPlates.Test/Features/Login/Account/LocalLoginAccountSeedTests.cs` | `GrumPlates.Test/Features/Accounts/Blazor/LocalLoginAccountSeedTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountAvailabilityTests.cs` | `GrumPlates.Test/Features/Accounts/AccountAvailabilityTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountConfigurationTests.cs` | `GrumPlates.Test/Features/Accounts/AccountConfigurationTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountCookieTests.cs` | `GrumPlates.Test/Features/Accounts/AccountCookieTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountDataManagementTests.cs` | `GrumPlates.Test/Features/Accounts/AccountDataManagementTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountEmailChangeTests.cs` | `GrumPlates.Test/Features/Accounts/AccountEmailChangeTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountEmailLifecycleTests.cs` | `GrumPlates.Test/Features/Accounts/AccountEmailLifecycleTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountFixtureTests.cs` | `GrumPlates.Test/Features/Accounts/AccountFixtureTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountGuardTests.cs` | `GrumPlates.Test/Features/Accounts/AccountGuardTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountMailOutboxTests.cs` | `GrumPlates.Test/Features/Accounts/AccountMailOutboxTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountMigrationTests.cs` | `GrumPlates.Test/Features/Accounts/AccountMigrationTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountPasswordTests.cs` | `GrumPlates.Test/Features/Accounts/AccountPasswordTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AccountReplicaOutboxTests.cs` | `GrumPlates.Test/Features/Accounts/AccountReplicaOutboxTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/AdminAccountSeedTests.cs` | `GrumPlates.Test/Features/Accounts/AdminAccountSeedTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/BlazorAccountAdaptersTests.cs` | `GrumPlates.Test/Features/Accounts/BlazorAccountAdaptersTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/BlazorBooksTransportTests.cs` | `GrumPlates.Test/Features/Accounts/BlazorBooksTransportTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/BlazorExternalAccountCompatibilityTests.cs` | `GrumPlates.Test/Features/Accounts/BlazorExternalAccountCompatibilityTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/CapturedMailReaderTests.cs` | `GrumPlates.Test/Features/Accounts/CapturedMailReaderTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/DataProtectionKeyImportTests.cs` | `GrumPlates.Test/Features/Accounts/DataProtectionKeyImportTests.cs` |
| `GrumPlates.Test/Features/Login/Accounts/PrivateBooksOwnershipTests.cs` | `GrumPlates.Test/Features/Accounts/PrivateBooksOwnershipTests.cs` |
| `GrumPlates.Test/Features/Login/HttpPrincipalCurrentUserAccessorTests.cs` | `GrumPlates.Test/Features/Accounts/Identity/HttpPrincipalCurrentUserAccessorTests.cs` |
| `GrumPlates/Features/Login/Account/AccountPageResultReader.cs` | `GrumPlates/Features/Accounts/Blazor/AccountPageResultReader.cs` |
| `GrumPlates/Features/Login/Account/AccountPasswordLengthAttribute.cs` | `GrumPlates/Features/Accounts/Blazor/AccountPasswordLengthAttribute.cs` |
| `GrumPlates/Features/Login/Account/AccountPasswordPolicyInputModel.cs` | `GrumPlates/Features/Accounts/Blazor/AccountPasswordPolicyInputModel.cs` |
| `GrumPlates/Features/Login/Account/ApplicationUser.cs` | `GrumPlates/Features/Accounts/Identity/ApplicationUser.cs` |
| `GrumPlates/Features/Login/Account/BlazorIdentityServiceCollectionExtensions.cs` | `GrumPlates/Features/Accounts/Blazor/BlazorIdentityServiceCollectionExtensions.cs` |
| `GrumPlates/Features/Login/Account/CurrentUserAccessor.cs` | `GrumPlates/Features/Accounts/Blazor/CurrentUserAccessor.cs` |
| `GrumPlates/Features/Login/Account/IdentityComponentsEndpointRouteBuilderExtensions.cs` | `GrumPlates/Features/Accounts/Blazor/IdentityComponentsEndpointRouteBuilderExtensions.cs` |
| `GrumPlates/Features/Login/Account/IdentityNoOpEmailSender.cs` | `GrumPlates/Features/Accounts/Identity/IdentityNoOpEmailSender.cs` |
| `GrumPlates/Features/Login/Account/IdentityRedirectManager.cs` | `GrumPlates/Features/Accounts/Blazor/IdentityRedirectManager.cs` |
| `GrumPlates/Features/Login/Account/IdentityRevalidatingAuthenticationStateProvider.cs` | `GrumPlates/Features/Accounts/Blazor/IdentityRevalidatingAuthenticationStateProvider.cs` |
| `GrumPlates/Features/Login/Account/LoginFeatureExtensions.cs` | `GrumPlates/Features/Accounts/Identity/IdentityServiceCollectionExtensions.cs` |
| `GrumPlates/Features/Login/Account/Pages/AccessDenied.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/AccessDenied.razor` |
| `GrumPlates/Features/Login/Account/Pages/ConfirmEmail.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/ConfirmEmail.razor` |
| `GrumPlates/Features/Login/Account/Pages/ConfirmEmailChange.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/ConfirmEmailChange.razor` |
| `GrumPlates/Features/Login/Account/Pages/ExternalLogin.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/ExternalLogin.razor` |
| `GrumPlates/Features/Login/Account/Pages/ForgotPassword.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/ForgotPassword.razor` |
| `GrumPlates/Features/Login/Account/Pages/ForgotPasswordConfirmation.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/ForgotPasswordConfirmation.razor` |
| `GrumPlates/Features/Login/Account/Pages/InvalidPasswordReset.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/InvalidPasswordReset.razor` |
| `GrumPlates/Features/Login/Account/Pages/InvalidUser.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/InvalidUser.razor` |
| `GrumPlates/Features/Login/Account/Pages/Lockout.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Lockout.razor` |
| `GrumPlates/Features/Login/Account/Pages/Login.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Login.razor` |
| `GrumPlates/Features/Login/Account/Pages/LoginWith2fa.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/LoginWith2fa.razor` |
| `GrumPlates/Features/Login/Account/Pages/LoginWithRecoveryCode.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/LoginWithRecoveryCode.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/ChangePassword.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/ChangePassword.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/DeletePersonalData.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/DeletePersonalData.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/Disable2fa.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/Disable2fa.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/Email.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/Email.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/EnableAuthenticator.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/EnableAuthenticator.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/ExternalLogins.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/ExternalLogins.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/GenerateRecoveryCodes.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/GenerateRecoveryCodes.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/Index.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/Index.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/Passkeys.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/Passkeys.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/PersonalData.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/PersonalData.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/RenamePasskey.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/RenamePasskey.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/ResetAuthenticator.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/ResetAuthenticator.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/SetPassword.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/SetPassword.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/TwoFactorAuthentication.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/TwoFactorAuthentication.razor` |
| `GrumPlates/Features/Login/Account/Pages/Manage/_Imports.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Manage/_Imports.razor` |
| `GrumPlates/Features/Login/Account/Pages/Register.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/Register.razor` |
| `GrumPlates/Features/Login/Account/Pages/RegisterConfirmation.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/RegisterConfirmation.razor` |
| `GrumPlates/Features/Login/Account/Pages/ResendEmailConfirmation.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/ResendEmailConfirmation.razor` |
| `GrumPlates/Features/Login/Account/Pages/ResetPassword.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/ResetPassword.razor` |
| `GrumPlates/Features/Login/Account/Pages/ResetPasswordConfirmation.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/ResetPasswordConfirmation.razor` |
| `GrumPlates/Features/Login/Account/Pages/_Imports.razor` | `GrumPlates/Features/Accounts/Blazor/Pages/_Imports.razor` |
| `GrumPlates/Features/Login/Account/PasskeyInputModel.cs` | `GrumPlates/Features/Accounts/Blazor/PasskeyInputModel.cs` |
| `GrumPlates/Features/Login/Account/PasskeyOperation.cs` | `GrumPlates/Features/Accounts/Blazor/PasskeyOperation.cs` |
| `GrumPlates/Features/Login/Account/Seed/LocalLoginAccountSeedExtensions.cs` | `GrumPlates/Features/Accounts/Blazor/Seed/LocalLoginAccountSeedExtensions.cs` |
| `GrumPlates/Features/Login/Account/Shared/ExternalLoginPicker.razor` | `GrumPlates/Features/Accounts/Blazor/Shared/ExternalLoginPicker.razor` |
| `GrumPlates/Features/Login/Account/Shared/ManageLayout.razor` | `GrumPlates/Features/Accounts/Blazor/Shared/ManageLayout.razor` |
| `GrumPlates/Features/Login/Account/Shared/ManageNavMenu.razor` | `GrumPlates/Features/Accounts/Blazor/Shared/ManageNavMenu.razor` |
| `GrumPlates/Features/Login/Account/Shared/PasskeySubmit.razor` | `GrumPlates/Features/Accounts/Blazor/Shared/PasskeySubmit.razor` |
| `GrumPlates/Features/Login/Account/Shared/PasskeySubmit.razor.js` | `GrumPlates/Features/Accounts/Blazor/Shared/PasskeySubmit.razor.js` |
| `GrumPlates/Features/Login/Account/Shared/ShowRecoveryCodes.razor` | `GrumPlates/Features/Accounts/Blazor/Shared/ShowRecoveryCodes.razor` |
| `GrumPlates/Features/Login/Account/Shared/StatusMessage.razor` | `GrumPlates/Features/Accounts/Blazor/Shared/StatusMessage.razor` |
| `GrumPlates/Features/Login/Account/_Imports.razor` | `GrumPlates/Features/Accounts/Blazor/_Imports.razor` |
| `GrumPlates/Features/Login/Accounts/AccountEndpoints.cs` | `GrumPlates/Features/Accounts/Endpoints/AccountEndpoints.cs` |
| `GrumPlates/Features/Login/Accounts/AccountFeatureExtensions.cs` | `GrumPlates/Features/Accounts/DependencyInjection.cs` |
| `GrumPlates/Features/Login/Accounts/AccountOperations.cs` | `GrumPlates/Features/Accounts/AccountOperations.cs` |
| `GrumPlates/Features/Login/Accounts/AccountOptions.cs` | `GrumPlates/Features/Accounts/AccountOptions.cs` |
| `GrumPlates/Features/Login/Accounts/AccountProblem.cs` | `GrumPlates/Features/Accounts/AccountProblem.cs` |
| `GrumPlates/Features/Login/Accounts/AccountRequestProtection.cs` | `GrumPlates/Features/Accounts/AccountRequestProtection.cs` |
| `GrumPlates/Features/Login/Accounts/AdminAccountSeed.cs` | `GrumPlates/Features/Accounts/AdminAccountSeed.cs` |
| `GrumPlates/Features/Login/Accounts/ClientConfiguration.cs` | `GrumPlates/Features/Accounts/ClientConfiguration.cs` |
| `GrumPlates/Features/Login/Accounts/Email/AccountEmailLinkFactory.cs` | `GrumPlates/Features/Accounts/Email/AccountEmailLinkFactory.cs` |
| `GrumPlates/Features/Login/Accounts/Email/AccountMailContracts.cs` | `GrumPlates/Features/Accounts/Email/AccountMailContracts.cs` |
| `GrumPlates/Features/Login/Accounts/Email/AccountMailHealth.cs` | `GrumPlates/Features/Accounts/Email/AccountMailHealth.cs` |
| `GrumPlates/Features/Login/Accounts/Email/AccountMailOutbox.cs` | `GrumPlates/Features/Accounts/Email/AccountMailOutbox.cs` |
| `GrumPlates/Features/Login/Accounts/Email/AccountMailOutboxWorker.cs` | `GrumPlates/Features/Accounts/Email/AccountMailOutboxWorker.cs` |
| `GrumPlates/Features/Login/Accounts/Email/AccountMailPayloadProtector.cs` | `GrumPlates/Features/Accounts/Email/AccountMailPayloadProtector.cs` |
| `GrumPlates/Features/Login/Accounts/Email/AccountMailTransport.cs` | `GrumPlates/Features/Accounts/Email/AccountMailTransport.cs` |
| `GrumPlates/Features/Login/Accounts/Management/AccountDeletionHandler.cs` | `GrumPlates/Features/Accounts/Management/AccountDeletionHandler.cs` |
| `GrumPlates/Features/Login/Accounts/Management/AccountEmailChangeHandler.cs` | `GrumPlates/Features/Accounts/Management/AccountEmailChangeHandler.cs` |
| `GrumPlates/Features/Login/Accounts/Management/AccountExportHandler.cs` | `GrumPlates/Features/Accounts/Management/AccountExportHandler.cs` |
| `GrumPlates/Features/Login/Accounts/Management/AccountPasswordChangeHandler.cs` | `GrumPlates/Features/Accounts/Management/AccountPasswordChangeHandler.cs` |
| `GrumPlates/Features/Login/Accounts/Persistence/AccountOutboxMessage.cs` | `GrumPlates/Features/Accounts/Persistence/AccountOutboxMessage.cs` |
| `GrumPlates/Features/Login/Accounts/Persistence/AccountUserLock.cs` | `GrumPlates/Features/Accounts/Persistence/AccountUserLock.cs` |
| `GrumPlates/Features/Login/Accounts/Recovery/AccountRecoveryHandler.cs` | `GrumPlates/Features/Accounts/Recovery/AccountRecoveryHandler.cs` |
| `GrumPlates/Features/Login/Accounts/Registration/AccountRegistrationHandler.cs` | `GrumPlates/Features/Accounts/Registration/AccountRegistrationHandler.cs` |
| `GrumPlates/Features/Login/Accounts/Security/AccountMutationTransactions.cs` | `GrumPlates/Features/Accounts/Security/AccountMutationTransactions.cs` |
| `GrumPlates/Features/Login/Accounts/Security/AccountOptionsValidator.cs` | `GrumPlates/Features/Accounts/Security/AccountOptionsValidator.cs` |
| `GrumPlates/Features/Login/Accounts/Security/AccountPasswordValidator.cs` | `GrumPlates/Features/Accounts/Security/AccountPasswordValidator.cs` |
| `GrumPlates/Features/Login/Accounts/Security/AccountPrincipalGuard.cs` | `GrumPlates/Features/Accounts/Security/AccountPrincipalGuard.cs` |
| `GrumPlates/Features/Login/Accounts/Security/AccountResults.cs` | `GrumPlates/Features/Accounts/Security/AccountResults.cs` |
| `GrumPlates/Features/Login/Accounts/Security/Resources/10k-most-common.txt` | `GrumPlates/Features/Accounts/Security/Resources/10k-most-common.txt` |
| `GrumPlates/Features/Login/Accounts/Security/Resources/README.md` | `GrumPlates/Features/Accounts/Security/Resources/README.md` |
| `GrumPlates/Features/Login/Accounts/Security/Resources/SecLists-LICENSE.txt` | `GrumPlates/Features/Accounts/Security/Resources/SecLists-LICENSE.txt` |
| `GrumPlates/Features/Login/Accounts/Session/AccountRevocationHandler.cs` | `GrumPlates/Features/Accounts/Session/AccountRevocationHandler.cs` |
| `GrumPlates/Features/Login/Accounts/Session/AccountSessionOperations.cs` | `GrumPlates/Features/Accounts/Session/AccountSessionOperations.cs` |
| `GrumPlates/Features/Login/HttpPrincipalCurrentUserAccessor.cs` | `GrumPlates/Features/Accounts/Identity/HttpPrincipalCurrentUserAccessor.cs` |
| `GrumPlates/Features/Login/ICurrentUserAccessor.cs` | `GrumPlates/Features/Accounts/Identity/ICurrentUserAccessor.cs` |
