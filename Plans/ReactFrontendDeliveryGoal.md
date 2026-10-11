# React frontend delivery goal

## Current owner direction (2026-10-11)

The owner requested removal of the extra demo repository and cleanup of the work created solely for it. This supersedes the earlier independent downstream demo delivery and additional-runner authorization. Keep this template as the only project repository. Do not recreate the demo repository, register another runner, enable its Actions, provision its app, or dispatch its deployment.

P0-P7 React implementation remains in the template alongside Blazor. Persistent controller SSH is complete and remains useful. Preserve both frontends, the existing Blazor deployment, its runner, working SSH keys/trust, and reusable setup tooling.

## Authorized cleanup

1. Delete only the owner-identified extra demo repository through authenticated GitHub access. Verify the exact target before deletion and verify absence afterwards. Deletion is verified after owner authentication: an authenticated owner request returned HTTP 404 for the exact target and the template repository remained accessible.
2. Remove the temporary candidate-readiness Actions secret and obsolete candidate installation notes, payloads, logs and the clean task-owned local clone. Verify ownership, resolved paths and absence of unrelated/uncommitted work before removal. The temporary Actions secret is removed; automatic approval review blocked local file/directory deletion, so local cleanup remains pending. Do not bypass that rejection or claim those files were removed.
3. Discard the unshipped additional-runner worktree and branch after confirming every change belongs to this task. No additional runner service, React app resource or deployment was created; do not invent node cleanup commands for resources that do not exist.
4. Retain the sanitized completed SSH/readiness evidence in [ReactFrontendProfile.md](ReactFrontendProfile.md#owner-scope-correction-and-cleanup-2026-10-11), remove the temporary coordination file, and repair its documentation references through a normal PR.
5. Require `build-test-push` on the cleanup PR's exact head before merging; record its merge and successful main CI. Markdown-only cleanup needs documentation review and `git diff --check`, not local builds/tests.

## Remaining product work

The prior separate-repository release/deployment sequence is withdrawn, not completed. A future public React delivery needs a reviewed release/deployment plan within this repository that preserves the Blazor default and current deployment. Do not silently switch the default profile or add a replacement repository to satisfy obsolete instructions. The public-only product and API/security contract remains in the profile plan; accounts remain deferred.

## Repository and host rules

Read `AGENTS.md` and current runbooks. Use a clean task worktree and explicit staged paths; preserve other tasks' changes. Never force-push main, commit private installation values/secrets, bootstrap this controller/WSL as a node, prune host resources, remove foreign resources or automatically reclaim a deployment lock. This cleanup does not authorize Cloud/LocalCluster dispatch or shared-service changes.
