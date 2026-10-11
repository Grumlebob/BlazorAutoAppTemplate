# React frontend delivery goal

Complete public-only React v1 and its separate public app on the existing native demo node, using only this repository and its existing Actions runner. The owner explicitly confirmed this outcome on 2026-10-11 after requesting removal of the extra demo repository. Keep the existing Blazor public app healthy and the template default `BlazorAuto`. Do not create another hosted repository or runner service.

## Read and verify before acting

Read `AGENTS.md`, [Test.md](../docs/Test.md), [ReactFrontendSingleRepository.md](ReactFrontendSingleRepository.md), and the product/security contracts and evidence in [ReactFrontendProfile.md](ReactFrontendProfile.md). Inspect current files, branch, remotes, worktrees, ownership, relevant PRs and exact check/merge state. Use clean task worktrees and explicit staged paths; preserve unrelated work. Do not restore deleted repository configuration or depend on obsolete local notes.

P0-P7 frontend implementation is complete. Persistent controller SSH is complete and verified working after cleanup. The extra hosted repository and temporary readiness secret are absent. The owner ran the reviewed manual cleanup script; subsequent checks verified the retired clone, eight scratch files, three log directories and script itself are absent. PR #163 cleanup head `a672f795a48101482b25682549c7f280f12b6c33` passed required run `38152925871`; merge `310dca9610419523c9f07412ed8ea6c0cb665ef4` passed main validation/publishing `38153407171`. Do not repeat cleanup or completed frontend packets absent a regression. Public React deployment is not complete.

## Remaining work

Execute replacement packets SR1-SR6 in the single-repository plan. Add optional additional-profile publishing to existing trusted main CI, retaining selected-only behavior for ordinary clones. Preserve primary image/artifact identities and publish React with its own immutable image/digest/manifest. Extend LocalSingleNode with validated per-app configuration using the existing runner. Add an owned-app-only setup route that preserves shared services and never repeats machine bootstrap.

Before owned setup/deployment, verify actual native host/ownership, ordinary collision checks, deployment-user Docker/workloads/capacity, existing Blazor health and fresh backups. Resolve the intended React origin and app settings privately; do not guess machine values or recover the retired repository. Continue independent implementation while private preferences are pending. Prefer verified controller SSH; use the existing native runner when established privileges require it.

Deploy only this repository's verified main React release through LocalSingleNode. Verify running source/digest/frontend/acceptance, LAN and independent public HTTPS/browser/denial checks, no accounts or anonymous writes, public seed persistence across one scoped React restart, Blazor health, backup/doctor/recovery, brief observation and fresh-clone/default/React/extension/release/deployment docs. Remove temporary inputs/secrets/scratch and completed task worktrees after evidence is retained.

## Product and authorization boundaries

React remains a public catalog/reference app using React Router SPA, TypeScript/Vite, TanStack Query, Tailwind, ASP.NET Core static hosting and generated OpenAPI public reads. Add no account UI, auth/session framework, mail/provider setup, private bookcase or anonymous writes. Preserve Blazor Identity, policies, private APIs and data.

The owner authorizes implementation and required local gates/tests, normal PRs/merges after exact-head `build-test-push` success, owned React public setup on the existing node, LocalSingleNode deployment of a verified immutable main release and one scoped React restart. Both apps use this repository and existing runner. Keep private machine values/credentials out of tracked files and public logs. Never dispatch Cloud/LocalCluster, bootstrap this Windows/WSL controller, broaden SSH/Docker/sudo privileges, run global prune, remove foreign resources, automatically reclaim locks, use Compose down with volumes, purchase services or disrupt unrelated shared services.

## Delivery completion

Keep the complete public delivery scope active across packets. Code/configuration needs the full local gate before push; build and test sequentially in each checkout. Require exact-head PR success, normal merge and green exact-main CI. Record merge/check/release/dispatch evidence in the plan or PR. Ordinary documentation-only work follows the current repository exception: review the complete diff, run `git diff --check`, use a PR and `[skip ci]` commits/squash title, then verify integrated `origin/main` content. Do not weaken enforced protection. Release provenance always remains exact.

Finish only when all SR1-SR6 and applicable profile requirements have authoritative evidence. The completed cleanup does not complete public React delivery. Mark blocked only after the same genuine impasse repeats for three consecutive goal turns with no meaningful independent work; pause only on explicit owner request.
