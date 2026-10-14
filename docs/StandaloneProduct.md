# Turn a fork into a standalone product

Use this when a fork becomes a product of its own instead of a configured copy of the template. The [fork guide](HowToForkThisRepo.md) still owns identity, runner variables and release settings; this page adds the order of work and the template material to remove.

## Create the repository

1. Create the empty product repository. Disable Actions until a runner for it exists (`gh api -X PUT repos/<owner>/<repo>/actions/permissions -F enabled=false`). Every job runs on self-hosted labels and otherwise queues indefinitely.
2. Clone the template with its history into a new folder. Rename its remote to `upstream`, add the product as `origin` and push `main`.
3. Run `gh repo set-default <owner>/<repo>` in the new checkout immediately. `gh` prefers a remote named `upstream`, so without it `gh pr merge`, `gh run list` and scripts that call `gh repo view` act on the template.
4. Commit one seed change for identity, frontend profile and release settings as described in the fork guide. Keep the internal project names until the rename step.

## Runners and plan limits

- On a personal GitHub account, a self-hosted runner belongs to one repository. A machine that already runs another repository's runner needs a second registration for this repository. The LocalSingleNode installer keeps each app's runner in its own folder. Set `CI_RUNNER_LABEL`, `CI_RUNNER_HOST` and the target runner label before enabling Actions.
- On GitHub Free, private repositories have no branch protection or rulesets. `build-test-push` is then required by the working rules in `AGENTS.md`, not by GitHub. Private images also count toward the account's GitHub Packages storage.

## Order of simplification

Each step is its own pull request with the [local gate](Test.md#local-gate) and an exact-head `build-test-push`. When PRs are stacked, retarget the dependent PR to `main` before merging the lower one.

1. **Seed** (above), with green CI.
2. **One frontend:** follow [React-only clone](Frontend/ReactOnlyClone.md) when Blazor is not needed.
3. **One deployment target:** follow [single-node-only clone](../Deployment/LocalSingleNode/SingleNodeOnlyClone.md) or the equivalent for the kept target.
4. **Rename** after the deletions, so deleted code is never renamed first:

   | Template name | Product name |
   | --- | --- |
   | `BlazorAutoApp.sln`, `BlazorAutoApp`, `.Core` and `.Test` projects, folders and root namespaces | `<Product>.sln`, `<Product>`, `<Product>.Core`, `<Product>.Test` |
   | `BlazorAutoApp.React`, npm package `blazor-auto-app-react` | `<Product>.React`, `<product>-react` |
   | Image labels `com.blazorautoapp.*` | A product label namespace. Change the Dockerfile, manifest writer and validator, release verifiers, smoke test, tests and deployment audit together |
   | Alloy container filter `blazorautoapp` in `docker/observability/alloy/config.alloy` | The product's Compose project name |

   Keep shared host names unchanged: the deployment lock `/tmp/localcluster-deploy.lockdir` and the CI resource labels are shared with other apps on the same machine. Run `api:check` afterwards; the generated contract should not change.
5. **Remove template material** (next section).
6. **Replace the sample feature** with the product's first use case. Use the [feature guide](HowToAddANewFeature.md), and remove the sample's data, tests, docs and observability with it.

## Remove template material

| Material | Action |
| --- | --- |
| `Plans/` template plans and `Plans/Support/` | Remove. Start the product's own plans and keep `Plans/README.md`. Git history and the template keep the old plans |
| Fork guide, this page, [React-only clone](Frontend/ReactOnlyClone.md), `SingleNodeOnlyClone.md` | Remove after use. The deployment audit reads the fork guide, so update the audit in the same code PR |
| `README.md`, `docs/Requirements.md` | Describe the product and its requirements. A one-line provenance link to the template is enough |
| `AGENTS.md` | Keep the working rules; drop rules for removed parts, such as the Razor stylesheet rebuild |
| `.claude/skills/`, `.codex/`, `.qlty/`, `.run/` | Keep what the team uses and update names and paths |
| `Scripts/Quality`, `docker/sonarqube` | Keep deliberately or remove with their docs |
| `.github/dependabot.yml` | Keep; update directories after renames |

Finish with a search and classify every match:

```bash
git grep -nIiE "BlazorAutoApp|blazor-auto-app|blazorautoapp|Books" -- ':!Plans'
```

Keep only provenance links, intentional shared names and recorded follow-ups.

## Public site behind Cloudflare

The React host sends a strict Content Security Policy (`script-src 'self'`; see `BlazorAutoApp/Frontend/ReactFrontendHosting.cs`). When the Cloudflare zone runs JavaScript detections, Cloudflare injects a script from `/cdn-cgi/challenge-platform/` that this policy blocks, and browsers log a CSP error. Choose one of two fixes:

- **Allow it with a per-response nonce.** [Portfolio #32](https://github.com/Grumlebob/Portfolio/pull/32) did this. The detection script then runs, and Lighthouse best practices dropped to 81 because of a deprecated API inside Cloudflare's script.
- **Exclude the hostname from JavaScript detections** in the zone. This gives up that bot signal.

The live browser tests already ignore Cloudflare's own edge cookies.

## Sharing a node with another product

Several apps can share a LocalSingleNode machine. Each app owns its Compose project, runtime root, Caddy site, ports and subnet, and shares Docker, Caddy and the deployment lock ([deployment overview](../Deployment/README.md)). [Application instances](../Deployment/LocalSingleNode/ApplicationInstances.md) covers only a second profile of the *same* repository.

A different repository on a node that already serves another app has no tested route yet. Start with the read-only [readiness and collision check](../Deployment/LocalSingleNode/Readiness.md) using the new app's candidate settings. Stop for an operator decision before any root command, and never change the other app's resources.
