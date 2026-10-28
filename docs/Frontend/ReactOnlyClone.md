# Make a React-only clone

Use this after forking when the product will ship only the React profile. The template keeps both profiles; this guide removes Blazor from a clone without leaving builds, CI, audit rules or docs that still expect it.

Start only after the clone selects `React` as described in the [fork guide](../HowToForkThisRepo.md#choose-the-frontend-and-sample-feature) and that change has a green CI. If the clone will also drop deployment targets, do this guide first, then the [single-node-only clone](../../Deployment/LocalSingleNode/SingleNodeOnlyClone.md), then any rename. Deleted code is then never renamed first. Land each step as its own pull request. The [standalone product guide](../StandaloneProduct.md) gives the full order.

## Inventory

List every match outside `Plans/` and classify it as remove, rewrite or keep:

```bash
git grep -nIE "BlazorAuto|GrumPlates\.Client|final-blazor|publish-blazor|\.razor|Blazor" -- ':!Plans'
```

Expect matches in these areas:

| Area | Paths | Action |
| --- | --- | --- |
| Client | `GrumPlates.Client/`, its solution and project references | Delete |
| Host UI | `GrumPlates/Components/`, Razor account pages under `GrumPlates/Features/Login/Account/`, `GrumPlates/Frontend/FrontendComposition.BlazorAuto.cs` | Delete; keep one React composition |
| React accounts | `GrumPlates.React/app/features/accounts/`, `app/routes/account.tsx`, `app/routes/auth-index.tsx`, `app/routes/my-books.tsx`, and the server account endpoints/storage | Keep the feature disabled for a public-only clone, or remove the full UI and server capability as a separate product change. Removing the UI alone does not protect the APIs or remove account data |
| Styles | `GrumPlates/wwwroot/tailwind.css`, `app.css`, `GrumPlates.Client/Styles` | Delete when only Razor uses them; React builds its own stylesheet |
| Build | `Directory.Build.targets`, `GrumPlates/GrumPlates.csproj`, `frontend-profile.txt` | Accept only `React`; fail clearly on `BlazorAuto`. The file holds `React` |
| Docker | `publish-blazor` and `final-blazor` stages in `GrumPlates/Dockerfile` | Remove; keep `final-react` |
| CI | `.github/workflows/ci.yml`, `Scripts/CI/validate-frontend-profiles.sh`, `Scripts/CI/publish_additional_frontend.sh`, `Scripts/CI/migration_staging_artifact.py`, `ADDITIONAL_FRONTEND_PROFILES` | Build, test and smoke React only; remove other-profile publication. Turn the profiles wrapper into one solution test script, as Portfolio did. Project paths follow the rename |
| Additional app | `Deployment/LocalSingleNode/ApplicationInstances.md`, `.github/workflows/localsinglenode-app-setup.yml`, `prepare-additional-app.sh`, `verify-additional-app.py`, the `app_instance` inputs of CD and maintenance | It exists only to run the other profile; remove it with its tests. Keep the primary identity and ownership checks in `resolve-app-instance.py` |
| Release tooling | `Scripts/Frontend/resolve_frontend_profile.py`, `Scripts/CI/write_release_manifest.py`, `Deployment/Common/Scripts/validate_release_manifest.py`, `Deployment/Common/ReleaseContract.md`, each kept target's `verify-release-identity.sh`, `Scripts/Test-DeployedSite.ps1`, `.github/workflows/cd-localsinglenode.yml`, `Deployment/LocalSingleNode/Scripts/lib/read_release_acceptance.py`, `Deployment/LocalSingleNode/ansible/roles/single_node_stack/` | Narrow to React profile and acceptance pairs, including the legacy manifest v1 notes, now or in a recorded follow-up |
| Other targets | `Deployment/LocalCluster/`, `.github/workflows/cd-localcluster.yml` | Delete with the single-node-only clone. If kept, narrow them like the release tooling |
| Local tooling | `docker-compose.yml`, `Scripts/RunLocal.ps1`, `Scripts/Testing/`, `GrumPlates.React/scripts/`, `.env.example` | Default to `final-react`; drop the `BlazorAuto` case and `GrumPlates.Client` roots. Names follow the rename |
| Repository config | `.gitattributes`, `.gitignore`, `.dockerignore`, `.qlty/qlty.toml`, `.github/dependabot.yml` | Drop the `*.razor` rule and the client Dependabot entries. Paths follow the rename |
| Names | `Deployment/Common/observability/`, `Deployment/LocalSingleNode/Scripts/lib/readiness.py` | Dashboards and the readiness user agent carry the project name. Rename with the project |
| Tests | `GrumPlates.Test/E2E/Support/BlazorE2ETestBase.cs`, Blazor E2E, render-mode and head-asset hosting tests, architecture tests naming the client, and script fixtures under `Scripts/CI/tests/`, `Deployment/Common/Scripts/Tests/` and `Deployment/LocalSingleNode/Scripts/Tests/` | Delete Blazor-only tests; make architecture and composition tests assert the React-only host; turn fixtures that name the Blazor profile into React ones |
| Browser tools | `axe-core` and `lighthouse` in `GrumPlates.Client/package.json`, used by `Scripts/RunLighthouse.ps1` and the axe tests | Move them to a test-only package with its own lockfile and Dependabot entry **before** deleting the client |
| Quality tools | `Scripts/Quality`, `docker/sonarqube` | Optional; remove with their docs when unused, as Portfolio did, and delete the CI step that runs their tests |
| Docs and rules | `AGENTS.md` (Tailwind rebuild rule), `README.md`, and every page under `docs/` that names the profile, such as [FrontendProfiles](../FrontendProfiles.md), [Blazor features](../Features/Blazor.md), the [feature guide](../HowToAddANewFeature.md) and [running locally](../HowToRunLocally.md) | Describe one frontend; delete the Blazor guide |

## Safe removal sequence

1. Branch from the clone's latest `main`.
2. Move anything React or tests still need out of the client first, including the browser tools and shared assets.
3. Change the entry points (MSBuild, Dockerfile, CI and profile validation) so nothing builds the Blazor profile. Then delete the client, Razor UI and Blazor composition.
4. Delete Blazor-only tests and rewrite the shared ones. The React profile must now run the whole suite. No test count is pinned, so nothing needs recording.
5. For every deployment-audit rule about a removed file or step, add a React-only rule, for example "no Blazor build path" or "no other-profile publication". Never only delete a rule.
6. Update the docs and rules listed above.
7. Run the inventory command again. Every remaining match must be intentional, such as provenance links, plan history or a recorded follow-up.
8. Run the [local gate](../Test.md#local-gate), open a PR and merge only after `build-test-push` succeeds on its exact head.

## Deliberate boundaries

- Narrowing the release resolver and verifiers touches deployment machinery. It may be a separate PR, but record it as a follow-up so no build can produce or accept a Blazor release.
- React accounts are optional and disabled by default. A public-only clone should keep them disabled; removing the feature requires a separate change covering the React UI, server authorization, Identity storage, migrations, deployment settings and recovery documentation. Removing the Razor account pages alone does not make those decisions. Treat PostgreSQL, Redis and the Books sample as separate product boundaries.

Worked example: [Portfolio #11](https://github.com/Grumlebob/Portfolio/pull/11) removed Blazor from the first clone, and its description lists each decision.
