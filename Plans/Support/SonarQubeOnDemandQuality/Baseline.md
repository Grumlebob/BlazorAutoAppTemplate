# Accepted SonarQube baseline

This is the first trusted full baseline for the merged tooling. It records two separate frontend compositions at the same source revision; profile LOC, issue counts, and coverage are not summed or averaged into a repository-wide value.

## Provenance

- Analyzed commit: `8393173bc4f580ae1dc036a533e4e47281099add` (PR #178 merge commit).
- Tooling PR head: `f8717708ddb1aecc2446ba3c8102c5142262f49d`; required `build-test-push` passed on that exact head.
- Main CI run `38183417500` completed green on the merge commit, including `build-test-push`.
- Full run: `full-20261011T232149Z-8393173bc4f5-e8a23ef3`; driver SHA and analyzed SHA both match the merge commit. The invoking feature checkout was `f8717708ddb1aecc2446ba3c8102c5142262f49d`.
- Mode `Full`; `candidate=false`, `dirty=false`, `baselineEligible=true`, outcome succeeded, archive verified, and both audit worktrees removed.
- Batch duration: 3m21s. BlazorAuto took 1m21s; React took 1m37s, sequentially.
- SonarQube was already running before the audit. The command neither started nor stopped it; it remains available on loopback for the requested MCP/UI review.
- Both profiles negotiated MCP protocol `2024-11-05`, exposed 15 read-only tools, and passed component-measures, quality-gate, coverage, issue, and rule queries.

## Toolchain and configuration

| Component | Version |
|---|---|
| SonarQube Community Build | `26.9.0.129388-community` |
| PostgreSQL | `17.11-alpine3.23` |
| SonarQube MCP | `1.28.0.4397` |
| `dotnet-sonarscanner` | `11.3.0` |
| `SonarAnalyzer.CSharp` | `10.35.0.4138` |
| .NET SDK | `10.0.303` |
| Node.js / npm | `24.21.0` / `12.2.0` |

Batch settings digest: `95b45c319e509b9f2fd3a4bed57f4d63e5d71d2c757642700e958cd2b17acb26`.

## Profile results

| Profile | Project key | Analysis ID | CE task | Tests | ncloc by language | Coverage | Duplication | Indexed files / open issues | Quality gate | Settings digest |
|---|---|---|---|---|---|---|---|---|---|---|
| BlazorAuto | `blazorautoapptemplate-5b8fdacf-BlazorAuto` | `bc2a9428-de35-4fc9-8668-bda773f0c8ec` | `389efd7c-41dd-42bc-89ba-cc134c651e7f` | .NET 211 passed, 0 failed, 13 expected skipped; React tests not applicable | 25,135 total: C# 9,920; CSS 447; Docker 56; JS 158; Python 14,286; Terraform 254; web 14 | 50.3% of 2,723 coverable lines; 28 production files with hits | 1.0% | 313 / 524 | OK (informational) | `ad5ab6ac4d975d45fce31c6832ee2dc43a6bbc8795b4d63f4a5d1c83145e1a00` |
| React | `blazorautoapptemplate-5b8fdacf-React` | `c52dbd2f-71aa-406e-bf73-f05a18b29f57` | `4d9d64b4-2bf9-400c-9da3-95f3830803b1` | .NET 203 passed, 0 failed, 13 expected skipped; React 31 passed, 0 skipped | 21,774 total: C# 5,695; CSS 374; Docker 56; JS 272; Python 14,286; Terraform 254; TypeScript 823; web 14 | 75.8% of 1,496 coverable lines; 47 production files with hits | 1.1% | 241 / 464 | OK (informational) | `1583d7f5c83c2d8401d3344e5059c98b61472407495f08bee3880689145ee41b` |

Software-quality impact counts were MAINTAINABILITY 475 / RELIABILITY 18 / SECURITY 31 for BlazorAuto and 412 / 24 / 34 for React. These impact categories can overlap on one issue; the unique open-issue totals are 524 and 464. Do not add the profile totals or infer that a green gate means zero issues.

## Scope and report evidence

- BlazorAuto scope checks found book geometry, book Razor, shared core, and handwritten CSS; the React implementation was excluded.
- React scope checks found the React composition, OpenAPI hosting, catalog page, and a tested API module with coverage; the Blazor implementation was excluded.
- Both reports were complete. Sonar returned zero open security hotspots with the endpoint marked supported-empty. No previous analysis existed, so this run is the starting snapshot; its “new issues” response is not a before/after comparison.
- The quality gate remains informational. Existing build, test, deployment, and review requirements remain authoritative.

The verified archive manifest records these report digests:

| File | SHA-256 |
|---|---|
| `batch.md` | `876070a47f4e6f2b5cd4bb6dfbe67bdc9a5051e898a8f80f8ce6bd73cd4ec096` |
| `summary.json` | `093d2231a5b74ce14a418fdab62eed0012c9546063ee42ca3f5bdf41c37a2288` |
| `BlazorAuto/report.md` | `3bc99b0d571a6be9b202dca2f869d8973390a6c7f304ea52a3b8affddf03672e` |
| `BlazorAuto/report.json` | `e370cffe9ef306063afcc7430e7d44bdac43129a224f724bac6dd87aed8e4cd4` |
| `React/report.md` | `55af6d6043ee464f96fa7df89fbcf5fb71d5417f3974cde0c487681bfb8a222f` |
| `React/report.json` | `b03fc95d4216a985922203204c159cdac7b834d9dbdf9cac26d181b4042934ca` |

The archive also includes per-profile settings and summaries. It excludes raw logs, test-result files, source excerpts, and worktrees. Paths to the per-user archive are kept in ignored local notes.

## Triage boundary

The first review classified representative security, reliability, coverage, and maintainability findings in [the improvement backlog](../../CodeQualityImprovements.md). Scanner severity and risk ranking guide review; they do not establish an application vulnerability by themselves. No application remediation was included in the tooling PR or this baseline.
