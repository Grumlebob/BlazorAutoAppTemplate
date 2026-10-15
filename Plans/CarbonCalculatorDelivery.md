# CarbonCalculator: product foundation, vertical slices and public delivery

Status: implementation plan; product implementation and deployment have not started.
Prepared: 2026-10-15. Owner decisions and provider conditions must be rechecked when execution starts.

Owner follow-up, 2026-10-15: an additional CarbonCalculator-specific runner registration on the existing native node is approved; preserve its current runner. Review accessible mockups before choosing the visual direction or early-beta versus complete-v1 launch timing. This decision does not start native setup or product deployment.

## 1. Outcome, authority and reading order

Deliver an independent, private [Grumlebob/CarbonCalculator](https://github.com/Grumlebob/CarbonCalculator) application at **https://carboncalculator.jacobgrum.com/**. Start from this template's ASP.NET Core backend and React frontend. Deploy only through LocalSingleNode on the owner's existing native Linux node. Reuse that machine and its installed infrastructure; verify runner scope before promising reuse of a registration. Preserve all existing applications.

The product estimates construction-material production impacts and freight scenarios. Users can explore real HGV routes without choosing a material, then add quantities and reviewed EPD records. Every result explains its inputs, method, provenance and limitations. The first release serves a Danish construction purchaser through an English interface, with a structure that supports Danish translation.

This request authorizes planning, source inspection, local design previews and preparation. It does not execute this product migration, register runners, alter the node, publish DNS or dispatch CD. A later instruction to execute this plan authorizes normal implementation and repository operations. Record its exact scope before live operations. Previous Portfolio or template deployment authority does not transfer automatically.

Read in this order:

1. This section, the preparation evidence and the three design directions in sections 2–3.
2. Product boundaries, architecture, contracts and free-service decisions in sections 4–9.
3. Packet protocol and ordered delivery work in sections 10–12.
4. Acceptance, operator dependencies, progress ledger and continuation instructions in sections 13–17.

All proposed CarbonCalculator paths, endpoints, commands and acceptance profiles below are **design targets until implemented**. Existing template links describe the inspected baseline; replace them with retained downstream runbooks when cleanup changes paths.

### What this plan replaces

The supplied **Calculator-Handoff / Complete Developer Handoff v3.0**, dated 2026-10-08, is source material, not an implementation or an instruction to create a Next.js application. Preserve its domain rules, datasets and acceptance IDs. This plan supersedes its framework, deployment, persistence, unauthenticated local-only assumptions and layer-first backlog.

Use [PortfolioStudioImplementation.md](PortfolioStudioImplementation.md) and [PortfolioStudioDeliveryGoal.md](PortfolioStudioDeliveryGoal.md) for delivery discipline: independent clone, safe identity before publishing, small PRs, vertical delivery, exact release evidence and closeout. Do not copy Portfolio's file-only runtime, static story prerendering, fresh-node bootstrap assumptions or deployment permissions. CarbonCalculator has interactive, network-dependent workflows and short-lived server state.

## 2. Preparation completed and evidence still missing

### Inspected on 2026-10-15

| Item | Observed evidence | Consequence |
| --- | --- | --- |
| Destination | GitHub API reports CarbonCalculator private and empty, with no default branch | Recheck before importing; never overwrite destination work |
| Destination Actions | Enabled; no registered repository runners | Disable before initial workflow push; enable only after routing is valid |
| Template source | Planning checkout started at `d0918b1a8b547c40105aa185896ae57e88db47fc` | Inspection checkpoint, not an approved product seed |
| Template CI | Exact-head CI [38729094671](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38729094671) still running at inspection | Choose a successful merged baseline during P01 |
| Earlier successful CI | [38723481502](https://github.com/Grumlebob/BlazorAutoAppTemplate/actions/runs/38723481502), SHA `78548cae3c91b6826133090caf6d0c5eab6a603f` | Evidence that a prior baseline passed, not a reason to ignore newer required fixes |
| Frontend | React 19.3.0, React Router 8.4.0 framework mode, Vite 8.3.4, Tailwind 4.3.3, TanStack Query, openapi-fetch | Reuse the pinned package/lockfile pair; do not install another framework |
| Rendering | `ssr:false`, with `prerender:["/"]` in the template | Remove route prerendering for the interactive product; retain the SPA shell |
| Runtime tooling | .NET SDK 10.0.300; frontend Node 24.21.0 and npm 12.2.0 | Recheck pins at seed time; handoff's Node 20+ is not the downstream version policy |
| Runner scope | The intended node's existing runner appears under the template repository; CarbonCalculator has zero runners | A personal repository runner cannot execute another repository's jobs |
| Release transport | [Template PR #290](https://github.com/Grumlebob/BlazorAutoAppTemplate/pull/290), immutable GHCR release payloads, was open | Inspect its final merged state before choosing the free-only release path |
| Source bundle | 15 files copied into ignored planning storage and verified by SHA-256 | Source is protected from Downloads being moved or deleted |
| Catalog | 11 records: five numeric-ready variants, six metadata-only | Broader taxonomy is permitted; numerical coverage must remain honest |
| Ferry registry | Two services; neither has approved live HGV terminals | Ferry comparison remains a separate release gate |
| Supplied tests | All 23 tests in `golden.test.mjs` and `materials.test.mjs` passed | Dataset arithmetic only; these tests implement their own example calculations |
| Live integrations | No routing key used; no live provider smoke test or terminal approach validated | Do not claim live route, ferry, production-app or public deployment acceptance |

Private preparation is under `Plans.local/CarbonCalculator/` in the controller's primary template checkout:

- `SourceHandoff/`: byte-preserving source copy; `SourceManifest.json` records path, byte count and SHA-256 for every file.
- `SourceInventory.json`: actual record IDs and current ferry approval state.
- `Mockups/index.html`: three self-contained responsive previews; no external fonts, tiles, libraries or API requests.
- `OperatorIntent.md`: source locations, requested existing node, current runner observations and handover locations. Keep installation details here, not in tracked scripts.

The previews are planning artifacts. Edited form fields do not recalculate numbers. All displayed sample routes are marked as fixture/schematic. The source bundle's `reviewedBy` text requests independent rechecking before external use; importing `approved` strings does not constitute a new numerical or rights review.

### Source review already performed

Read the full handoff, routing notes, release checklist, supplied tests and data structure. Opened the five official EPD PDFs, provider migration notice, routing restrictions, OSM tile policy, GitHub runner/billing documentation and ÖKOBAUDAT data-user guidance. This establishes relevant source locations and current policy evidence. It does not grant data redistribution rights or replace the per-field review in P09/P15.

## 3. Early visual directions: choose before building the full UI

The three local previews deliberately use the same Hamburg timber fixture, so layout and hierarchy can be compared. They include desktop/mobile layouts and example explanation drawers. None is a working calculator. Do not mistake the schematic map for a geographically accurate basemap.

| Direction | Character and layout | Initial tokens | Tradeoff |
| --- | --- | --- | --- |
| **A — Fieldwork, recommended** | Calm construction workspace; left input panel, map and corridor comparison, separate production/freight cards, evidence drawer | Background `#F4F6F2`, surface `#FFFFFF`, ink `#1E382E`, accent `#24734F`, tinted surface `#EDF4E9`, 12 px card radius | Easiest introduction for beginners; advanced users need expandable detail |
| **B — Route Desk** | Dark technical workspace; larger map, compact controls, route details emphasized | Background `#0E1A25`, surface `#172736`, ink `#E6EEF5`, accent `#4B82D4`, 7 px radius | Efficient for frequent routing; denser first impression |
| **C — Material Ledger** | Warm report workspace; production and freight figures before map; editorial headings and clear source ledger | Background `#F5F0E7`, surface `#FFFCF7`, ink `#39382D`, accent `#6D7248`, 5 px radius | Strong report readability; route exploration receives less space |

Portable composition briefs:

```text
A / Fieldwork
  Header: brand | Calculator | Route explorer | Sources & method
  Intro: product purpose + scenario-estimate qualification
  Inputs 360–400 px | Route map, source legend, selected corridor
                   | Three corridor cards; explicit provisional selection
                   | Production A1–A3 card | Freight WTW card
                   | Evidence summary and next useful improvement

B / Route Desk
  Compact header and transport status
  Dense input panel | Large map and per-leg sources
                    | Selectable corridor table and ranking sensitivity
                    | Production and freight inspector

C / Material Ledger
  Editorial header and scenario title
  Inputs | Production card | Freight card
         | Boundary and source summary
         | Supporting map and route alternatives
         | Report actions and provenance ledger
```

### Design decision gate

1. Present A/B/C to the owner before final component implementation. Record selected direction and specific changes. **A is a recommendation, not approval.** Independent source, repo and contract work can continue while the owner considers it.
2. Produce the chosen calculator view, Route Explorer, result explanation, printable report and empty/error examples at desktop and mobile sizes.
3. Use local system fonts initially. Establish CSS variables for color, spacing, type, focus, warnings and source status. Keep semantic components small and reusable.
4. Validate at 320, 390, 768, 1024 and 1440 CSS px, including 200% text zoom. Mobile stacks inputs before results; a sticky action must not cover content or focus.
5. Ensure keyboard operation, visible focus, accessible autocomplete selection, text alternatives to map controls and route line patterns. Status must never depend on color alone.
6. Do not decorate a modelled route or proxy match with a general green “verified” badge. Distinguish source authenticity from product fit and route certainty.
7. Archive selected screenshots and a compact design specification in the downstream product. Keep rejected previews out of production assets. This plan contains enough composition/tokens to reconstruct the directions if ignored files are unavailable.

The first production UI is a calculator, not a marketing dashboard. No invented customers, savings percentages, certifications, shipment activity or carbon-neutral claims. Initial light theme follows the selected design; a complete dark theme is an expansion packet unless the owner selects B as the primary direction.

## 4. Product contract and scope

### Required for the complete first delivery

- Real address/city search with candidate confirmation and explicit location precision.
- Shared Route Explorer: arbitrary supported origin/destination, optional waypoints, HGV restrictions and ferry policy, usable without a material.
- Default live HGV road routing through the backend. No key or provider failure produces a useful unavailable/setup state and an explicitly selected offline sample.
- Five genuinely usable EPD variants: sawn timber, SHT precast wall, RT247 brick, Thermocell loose wool and ThermoWhite WD100 floor insulation.
- Searchable broader material taxonomy; steel/board/CLT and other metadata remain nonnumeric until reviewed.
- Explicit proxy consent or transport-only continuation; production and dispatch locations remain separate.
- Mass/volume/quantity conversion, load allocation, product restrictions, known/unknown route controls and stale-result handling.
- Live road/ferry comparison for both configured services and both eligible directions after terminal approval. Complete inference requires validated approaches, not fixture-only ferry cards.
- Deterministic, explainable route recommendation, ambiguity and waiting-time sensitivity.
- One shipment plus a known intermediate warehouse, typed movements and a lifecycle ledger. Show unknown upstream facts without fabricating suppliers.
- Independent A1–A3 indicators and freight WTW estimates, source explanations, JSON export/import, immutable report and print view.
- A reviewed, bounded ÖKOBAUDAT importer and at least one approved second-provider dataset. This retains the handoff's concrete data-expansion commitment.
- Public SPA at the requested hostname, with provider quotas, privacy behavior, operational checks, update/rollback and app-data restore evidence.

### Milestones are distinct

| Milestone | Meaning |
| --- | --- |
| Foundation ready | Independent private repo; own identity; React/LocalSingleNode only; working CI |
| Live road slice ready | New locations produce live HGV geometry through the real UI and backend |
| Calculation preview ready | Five EPD scenarios, correct ledger and private report workflow work end to end |
| Public road beta | Optional early release, with explicit owner agreement and truthful “ferry comparison not yet available” label |
| Complete v1 delivered | All mandatory slices and public/recovery gates pass, including reviewed ferry inference and second-provider import |

A public road beta does not complete this plan. Do not silently drop ferry validation, the second provider, or beginner evaluation. If an external dependency remains unavailable, record it and continue independent work. Only the owner can explicitly defer required scope.

### Deliberate expansion backlog

Keep these outside v1 unless the owner promotes a packet: accounts and cloud project storage; organizations and role permissions; shareable private reports; multi-material projects and mixed-load allocation; carrier documents/uploads; digital authorized EPD APIs; real fleet/fuel factors; pricing/tolls/schedules; additional freight modes; building-scale LCA; paid plans; full Danish translation; dark theme; analytics; AI assistance. Never let speculative supplier discovery replace evidence.

## 5. Selected architecture

### Runtime and ownership

Use a **modular monolith with vertical feature slices**. ASP.NET Core owns validation, calculations, source matching, provider calls, immutable snapshots and persistence. React owns interaction and display. One app image serves the SPA and same-origin API. Node is a build/development dependency, not a second production server.

Use React Router framework mode already present in the template, with `ssr:false` and no route prerender list for the calculator. The build may create the framework's static boot shell; this is not prerendering scenario results. Interactivity alone does not forbid prerendering, but mutable private scenarios and provider calls do not benefit from Portfolio's per-content static export. A future public landing/methodology page can introduce prerendering in a separate measured change.

Use Tailwind and a small local component set. Add React Leaflet/Leaflet only after checking compatibility with the pinned React version and license. Lazy-load the map. Prefer native controls; use an accessible headless primitive when keyboard behavior warrants it. No Next.js, Drizzle, second API server, Redux, message broker, generic repository layer or mediator dependency is required.

Keep TanStack Query/openapi-fetch and generated OpenAPI types. C# DTOs and endpoint metadata are the wire contract authority. Regenerate through the inherited `api:generate`/`api:check` workflow; do not separately maintain handwritten TypeScript API DTOs. Small UI form types are permitted.

### Proposed downstream layout

```text
CarbonCalculator.sln
CarbonCalculator/
  Features/
    Capabilities/                   # safe operator-independent availability
    RouteExplorer/
      SearchPlaces/                 # endpoint, request, handler, validation
      FindRoutes/
      GetRouteCatalog/
    Materials/
      SearchCatalog/
      GetRecord/
      AssessMatch/
    Calculations/
      CreateEstimate/
      Recalculate/
    Reports/
      ReadSnapshot/
      DeleteSnapshot/
  Infrastructure/
    Providers/HeiGit/
    Persistence/                    # SQLite, migrations and retention
    Security/                       # capabilities, rate limits, safe errors
  Frontend/                         # SPA/static hosting and security headers
CarbonCalculator.Core/
  Routing/                          # typed legs, feasibility and ranking
  Materials/                        # units, EPD variants and matching
  Calculations/                     # loads, indicator math and ledger
  Provenance/                       # source references, revisions, explanations
CarbonCalculator.React/
  app/features/{route-explorer,materials,calculator,reports,sources}/
  app/routes/                       # thin route composition
  app/api/                          # generated contract/client/query keys
  app/components/                   # genuinely shared UI primitives
CarbonCalculator.DataTool/          # offline validation and staged imports
CarbonCalculator.Test/
  Features/{RouteExplorer,Materials,Calculations,Reports}/
  Domain/ Infrastructure/ E2E/
Data/{Catalogs,Factors,Ferries,Scenarios,Fixtures}/
Deployment/{Common,LocalSingleNode}/
Plans/CarbonCalculatorDelivery.md
docs/{Requirements,Architecture,Test,Operations,DataSources}.md
```

Do not create one project per feature or a graph platform. Core contains pure shared domain rules; host feature directories contain use-case behavior. React features may import shared API/UI helpers, not reach into another feature's internal state. Route Explorer and calculator invoke the same routing handlers/domain policies.

### One slice's implementation pattern

For example, `FindRoutes` owns its validated request/response, endpoint mapping, orchestration, generated contract change, React query and route cards, failure cases, tests and acceptance evidence. Its handler calls a typed provider adapter and pure ranking policies. Domain calculations never call HTTP or depend on React.

Cross-cutting concerns enter through a small composition root. Use direct dependency injection and handlers; do not introduce abstraction for hypothetical providers. Add `ITruckRouter`, `IPlaceSearch`, `IEpdCatalog`, `IReportStore` and `IProviderCache` only at actual external/persistence boundaries. Concrete names may follow existing conventions after baseline inspection.

### Persistence decision

Use EF Core SQLite for the single-node product, with one owned persistent volume. Keep immutable reviewed catalog/factor files in Git; persist short-lived provider cache entries, route-set envelopes and anonymous report snapshots. Add a simple hosted retention task. The initial schema needs these few records, not every speculative table in the handoff.

Remove inherited PostgreSQL, Redis, Books, Identity, email, social login, passkeys, account migrations and their runtime dependencies together once product endpoints replace the sample. Remove obsolete health probes, dashboards, Compose services, secrets, packages, migration assumptions and acceptance fixtures too. Keep ASP.NET security, diagnostics and the migration/release interface needed by SQLite.

SQLite rules: one application replica initially; WAL and finite busy timeout; short transactions; never hold a write transaction during a provider call; owned non-root writable data directory; bounded report/body/cache sizes; proper online SQLite backup or a documented quiesced backup. Copying an active `.db` without its consistency protocol is not a verified backup. More replicas or large collaboration needs trigger a database ADR, not shared SQLite over a network filesystem.

Do not remove release manifest verification because database technology changes. Regenerate the SQLite migration bundle, update Linux runtime/native dependencies, deployment migrations, backup/doctor checks and release tests in the same packet.

## 6. Domain model and numerical invariants

### Small typed model

| Concept | Required distinctions |
| --- | --- |
| Quantity | Original value/unit; normalized mass/volume; user/derived/assumed origin; conversion source |
| Place selection | Coordinates, precision, role, user confirmation, provider/source revision; text and coordinates invalidate together |
| Material lot | Product family/variant, quantity, product system, optional EPD selection and explicit proxy consent |
| EPD variant | Operator, record/variant IDs, unit, standard, geography, validity, reviewed numeric fields and rights status |
| Vehicle/load | Tare, payload, gross limit, dimensions, volume, source assumptions; individual allocations when split |
| Movement | Origin/destination, lot identity, known waypoints, boundary attribution, selected candidate |
| Freight leg | Road/ferry mode; geometry, distance, duration, completeness; separate evidence and source timestamps |
| Route set | Normalized input fingerprint, vehicle restrictions, candidate/exclusion list, provider versions and expiry |
| Indicator result | Named method/module/indicator, quantity, unit, formula, source and assumption references |
| Boundary ledger | Counted/excluded/unresolved decision with reason, product system and movement IDs |
| Calculation snapshot | Immutable input/result/source/geometry/revision snapshot with original and current method versions distinguished |

Avoid a single `verified` or `live` boolean. Record independently: authentic EPD source, reviewer status, product fit, location precision, live-model road provenance, reference/schematic ferry provenance, generic factor quality and user declaration. A live ORS model is not a measured shipment.

Use C# `decimal` for entered quantities, published factors and impact arithmetic, with explicit unit wrappers or named value types. Use finite bounded `double` for provider coordinates/geometries and provider distance/duration, converting once through a documented invariant conversion before emissions arithmetic. Preserve source scientific notation beside normalized values. Never round intermediate quantities. JavaScript displays server results; it does not maintain another authoritative calculator.

JSON uses validated finite numbers and ISO UTC times. Document hash canonicalization, property ordering, invariant numeric representation and LF encoding. Content/data revision must match on Windows and Linux. Generated TS numeric types do not promise arbitrary decimal precision; exports retain the authoritative snapshot and source values. Test numeric equivalence with the handoff's tolerances and separate display-rounding assertions.

### Essential accounting rules

1. `massKg = tonnes × 1000`. `volumeM3 = massKg / sourcedDensity`. Declared-unit scaling divides by the EPD's actual declared amount, which need not equal one.
2. Missing density, piece mass, area or thickness stays missing. Ask for a documented conversion or user-labelled assumption. No average density silently selected from a range.
3. Production impacts are computed once per material lot, not once per truck or scenario alternative.
4. Freight per leg is `cargoTonnes × legKm × compatibleFactor`. Sum only eligible legs with compatible WTW indicators. An operator CO₂ value or vehicle-km factor follows another method and cannot enter this sum accidentally.
5. Do not multiply total cargo tonnes by truck count again. Source-average cargo-tkm allocation and vehicle-fuel calculation are mutually exclusive calculation paths.
6. Per-load routing restrictions use the load's actual modelled gross mass. A 20 t cargo plus 15 t tare requires 35 t; not 20 t. If different split loads require different route restrictions, route each distinct restriction profile or use an explicitly conservative shared profile and disclose it.
7. For divisible homogeneous cargo, loads are the maximum of weight- and volume-required loads, using positive feasible capacities. 60 t with 25 t payload requires 25/25/10 t loads. Indivisible oversize cargo requires manual logistics review.
8. A1–A3 already covers its included upstream inventory. An upstream node can be educationally visible while excluded from additive freight. Never count both generic EPD A4 and the replacement custom A4.
9. Movement to another factory is not automatically A4. Warehouse legs count once when they remain finished-product delivery to site. Preserve unresolved boundary attribution instead of guessing.
10. Never sum material `GWP-fossil`, `GWP-total` and freight `WTW-CO2e` into one official A1–A4 total. Wood's negative A1–A3 total needs a biogenic/whole-life explanation, not a climate-negative headline.
11. No unknown numerical field becomes zero. Negative EPD indicators can be valid; negative mass/distance/duration/factor cannot.
12. Edits mark previous route/results stale. Server fingerprints prevent mixing a new mass, EPD, geometry or truck with old results.

### Initial source-based numerical acceptance

These are source-bundle goldens, pending the independent publication review. Preserve indicator and variant identity.

| Case | Expected A1–A3 GWP-fossil | Other required result |
| --- | ---: | --- |
| 20 t timber, `MD-25104-EN` | 1,180.327868852459 kg CO₂e | 40.98360655737705 m³ at 488 kg/m³; Sweden/Finland proxy warning for unknown Hamburg manufacture |
| 12 t SHT wall, `MD-23236-DA` | 1,812 kg CO₂e | Wall elements, not ready-mix concrete |
| 10 t brick, `MD-25038-EN-Rev1:RT247` | 495 kg CO₂e | Never reuse for RT248/RT578/RT579 |
| 500 kg Thermocell, `MD-23179-EN-Rev1` | 478 kg CO₂e | No invented single density from the published range |
| 15 m³ ThermoWhite, `MD-23094-DA-Rev1:WD100` | 792 kg CO₂e | Freight cargo mass 1.53 t at 102 kg/m³ |

The fixture's road-only/Puttgarden/Rostock transport values are 824.0 / 550.24 / 680.224 kg WTW CO₂e with the illustrative 0.080 road and 0.1156 ferry factors. Alternate 0.101 road values are 1,040.30 / 682.54 / 827.224 kg. These are **offline fixture goldens**, never assertions for live distances.

Preserve all reported EPD indicators individually. The timber source reports rounded fossil/biogenic/luluc/total values; do not enforce exact addition of independently rounded components. The official [timber PDF](https://www.epddanmark.dk/media/y1wfvthh/md-25104-en.pdf), pp. 4–6, is the numerical source, not the mockup.

## 7. Routes, sources and explanations

### Live provider behavior

All provider requests originate in ASP.NET through typed `HttpClient` adapters. The supported HeiGIT migration is documented in the [official provider notice](https://ask.openrouteservice.org/t/deprecating-api-openrouteservice-org-in-favour-of-api-heigit-org/7912):

- Directions: `POST https://api.heigit.org/openrouteservice/v2/directions/driving-hgv/geojson`.
- Place search: `https://api.heigit.org/pelias/v1/search` with its verified server-side authentication contract.
- Directions use `options.vehicle_type=hgv`, `avoid_features=["ferries"]`, and normalized loaded vehicle restrictions on every road leg.
- Convert `[lon, lat]` only at GeoJSON/provider boundaries. Reject invalid geometry, nonfinite values, coordinate reversal, unreasonable snapping and missing/negative summaries.
- Do not request unsupported long-distance alternatives; generate named ferry candidates through separate road requests. Validate current [provider restrictions](https://openrouteservice.org/restrictions/) and account quotas instead of hard-coding remembered allowances.

A historical notice schedules the old host's removal for 2–6 November 2026. Active code must use the new host immediately; test assertions may mention the old host only to reject it. Configure allowlisted provider bases server-side, never through arbitrary public request URLs.

Confirm candidates before routing. A company name is a search hint, not evidence that its legal headquarters is the factory. Country-only input produces no precise facility route unless the user explicitly chooses a labelled illustrative reference or reference set; preserve that uncertainty through report/export. No location means no route, while material per-unit results can remain available.

### Candidate construction and ranking

1. Validate selected places, route knowledge, vehicle and cargo allocations. Normalize optional known warehouse/waypoints without removing real movements.
2. Request the ferry-free road candidate. Its failure does not automatically prove all ferry approaches fail: evaluate eligible alternatives within the request budget and return explicit exclusions.
3. Prefilter each configured ferry direction by geographic plausibility and service support. Use deterministic geometry/lower bounds, not city-name hard-coding.
4. Reject unapproved terminal coordinates. For an approved direction, route origin to freight entrance and arrival truck exit to destination as separate ferry-free HGV requests.
5. Insert a separately sourced sea leg. Its geometry remains schematic unless verified licensed geometry exists. Do not describe the entire candidate as wholly live-measured.
6. Validate continuity, terminal snapping, no road ferry segments, feasible loads, no repeated/reverse crossings, deduplication and explicit incomplete/excluded reasons.
7. Score complete candidates by road minutes + reference sailing minutes + per-crossing terminal buffer. Default 45 min; show 15/45/90 min sensitivity.
8. Sort by effort, then fewer ferries, road km and stable candidate ID. If the next candidate is within `max(30 min, first effort × 10%)`, show `no_clear_preference`.
9. Above 2× best effort, group a feasible detour under additional alternatives, not prominently plausible corridors. Required named route constraints never silently fall back to another ferry or road.
10. User override changes selected map, per-leg emissions, explanation and snapshot. It remains user-declared, not independently documented. Carbon comparison never masquerades as carrier-choice probability.

With the fixture, 45 min buffer gives 340/390/455 min and a provisional Puttgarden preference. At 90 min, 385 versus 390 min is ambiguous; sensitivity must report changes in ambiguity **even if the first-ranked ID stays the same**.

### Ferry approval is directional

The supplied registry has four ports, each with unapproved entrance/exit fields. Define reviewed entrance **and** exit data for all enabled directions; one approved port-centre point or one-direction test does not approve the reverse direction. Keep service dates/status, accompanied-HGV eligibility, operator source, terminal revision, review timestamp, snap evidence and maximum accepted endpoint gap.

Research current official freight instructions and maps first. The agent can do this research and live road checks. Ask the owner for extra evidence only if official/public sources cannot establish the truck access. No owner site visit is assumed. Failed/unresolved approaches keep that direction disabled. A global `liveHgvTerminalsApproved=true` must be derived from its required direction approvals, not toggled to satisfy a test.

### Source and explanation graph

Every nontrivial number references a source or named assumption, including density, truck defaults, wait buffer and generic factor. Store original document/revision/page/table, retrieval/review time, method/module/indicator, rights state and transformation. Reviewed source authenticity does not imply exact supplier fit.

Build explanations from the same calculation nodes used for the result and report. A drawer shows: what this number means; substituted formula with units; original source; user inputs; assumptions; boundary decision; and the next useful improvement. Do not maintain a second hard-coded explanation calculator.

Keep provenance dimensions visible in UI, print and JSON. Route-cache hits retain the original provider retrieval time plus current served time. Do not call a seven-day-old cached model a fresh live request.

## 8. Public API, anonymous privacy and failure contracts

### Proposed API

Use `/api/v1` with generated OpenAPI, cancellation propagation, bounded DTOs and safe ProblemDetails. Template `/health/live` and readiness checks retain their operational purpose; provider outages should not restart a healthy process.

| Endpoint | Contract |
| --- | --- |
| `GET /api/v1/capabilities` | Safe live-routing configured/temporarily unavailable state, catalog/method versions and enabled ferries; no key fragments, host paths or raw provider details |
| `POST /api/v1/places/search` | Search text/country hint; selectable candidates with precision/source. Ambiguity is a valid candidate list, not an automatic 422 |
| `GET /api/v1/materials` | Taxonomy and permitted units, independent of numerical coverage |
| `GET /api/v1/epds` | Query/filter with explicit numeric/metadata status and fit warnings |
| `GET /api/v1/epds/{recordId}` | Approved fields and source details; exact variant IDs remain intact |
| `GET /api/v1/routes/catalog` | Configured ferry directions, availability and exclusion reasons |
| `POST /api/v1/routes` | Confirmed places, route knowledge, explicit live/demo mode, vehicle/cargo; returns route-set ID, fingerprint, expiry, candidates and recommendation |
| `POST /api/v1/calculations` | User inputs, selected reviewed EPD/factors and server-issued route-set/selection; returns immutable snapshot plus short-lived report access capability |
| `POST /api/v1/calculations/recalculate` | Prior report capability or validated imported inputs plus overrides; creates a new snapshot and never mutates the old one |
| `GET /api/v1/reports/{id}` | Snapshot only, with capability header; no provider calls or recalculation |
| `DELETE /api/v1/reports/{id}` | Delete this report with its capability; document retention/backup limits |

Server-issued route-set data prevents a caller substituting invented distances into an official-looking result. Bind it to normalized input, mode, method/provider revisions and vehicle settings; reject expired/mismatched sets. A reference by ID alone is not authorization. Use an independent route-set capability or a signed, short-lived server envelope. Never trust client-supplied factor values or EPD impacts; resolve approved revisions server-side.

Suggested failures: 400 malformed JSON; 422 field/domain errors; 404 inaccessible/expired/unknown report; 429 local or upstream quota with safe Retry-After; 502 malformed upstream response; 503 provider unavailable/unconfigured; 504 timeout. Expose stable `code`, field errors, correlation ID and safe retry guidance. Valid but incomplete coverage can be a 200 typed partial result; it must not contain zero-filled missing legs. Do not return provider bodies or secrets.

### Anonymous report design

The handoff's no-auth local database assumption is unsafe for public reports. Keep the initial product account-free, with bounded anonymous use:

1. A report has a random ID and an independent cryptographically random capability of at least 256 bits. Store only its hash, compare safely, and require it in a dedicated header. Knowing an ID does not grant access. There is no report enumeration endpoint.
2. Default capability/report-input state stays in the tab's `sessionStorage` or memory. Never put addresses, capabilities or whole scenarios in URLs, analytics, source maps, third-party query strings or logs. Explain that local browser scripts can access tab storage; enforce CSP and prevent injection.
3. Server report retention defaults to 24 hours, bounded by configurable storage and request size limits. Expired reports are not served. Run deletion regularly and document backup expiry separately; do not promise instantaneous erasure from existing backups.
4. No public share link, user uploads or permanent project store in v1. Explicit JSON export is the durable user-owned copy. Add “Clear this session” and report deletion with an explanation of remaining exports/backups.
5. Route/geocode caching uses a separate documented retention policy, initially up to seven days only if provider terms allow. A hash cache key does not anonymize a payload containing precise coordinates. Limit collected data and restrict volume/backup access.
6. JSON import is untrusted: enforce schema/version, byte/count/depth limits, finite numbers and safe text/URLs; render no executable HTML. Imported values are labelled imported, not server-verified. Recalculate only after confirmation and new server validation.
7. Reopening a snapshot must not fetch routing, quietly refresh factors or change any number. Recalculation creates a new ID with an explicit change summary.

Frontend routes: `/` calculator, `/routes` explorer, `/materials` catalog, `/sources`, `/methodology`, `/reports/:id` capability-controlled report view, `/privacy` and client not-found. Direct navigation and refresh must work. ASP.NET returns true API/asset/reserved-path errors; unknown navigation paths should return a 404 shell through a constrained product route policy rather than turn `/api/*` errors into HTML. Keep reports `no-store` and excluded from indexing. Public catalog caching is separate from private scenario caching.

### Quota and abuse controls

- Server-only provider key; no `VITE_*`, `REACT_*` or other browser-exposed secret. Use user secrets/private environment locally and the existing protected deployment secret path in production.
- Configure request/body/geometry/waypoint/candidate limits. Start with at most three user via points and the two configured ferries; expose the product limit rather than the provider maximum.
- Search on submit first. Add debounced autocomplete only after quota accounting; cancel superseded requests and never silently choose the first place.
- Initial provider timeout: 20 seconds; bounded total route operation with cancellation and at most one transient retry. Do not retry authentication, validation or quota failures automatically.
- Server cache keyed by exact confirmed coordinates, route options, load restrictions, provider/profile/version, waypoint order and ferry terminal revision. Deduplicate simultaneous identical calls.
- Account-wide provider request budget applies to each underlying leg/search call, retries included. Persist daily counters across restarts; configure limits from actual account allowance with a reserve and provider reset timezone. Include a per-minute budget and a global concurrency cap.
- Per-client rate limits supplement the global budget. Trust forwarded addresses only from the known Caddy/Cloudflare chain. Do not accept arbitrary spoofed `X-Forwarded-For` as identity.
- No automatic focus/reconnect refetch or default mutation retry for expensive routing. Route only on explicit submitted inputs. Returning cached results is labelled with retrieval time.
- Tests and public acceptance use deterministic fixtures by default. Live calls are a bounded, explicit integration stage; scheduled health checks must not consume the daily routing budget.

## 9. Free-only dependencies and policy evidence

The owner permits free software/free tiers now. No automatic paid upgrade, paid API key, card-required trial or unbounded usage charge. Treat future paid services as a new decision, not an assumed escape hatch.

| Dependency | Initial choice | Release evidence and fallback |
| --- | --- | --- |
| App hosting | Existing native LocalSingleNode machine | Capacity/collision audit; no new hosting subscription |
| CI runner | Existing machine, CarbonCalculator-eligible registration | Verify repo access; no hosted runner fallback that can spend minutes unexpectedly |
| Release images/payload | Private GHCR package owned by CarbonCalculator | GitHub currently exempts Container registry image storage/bandwidth from charges; keep a retention policy and recheck before launch |
| Actions artifacts/cache | Avoid a mandatory metered storage path | Prefer verified merged #290 transport; otherwise adapt an audited equivalent downstream or explicitly cap evidence storage within remaining allowance |
| Routing/geocoding | Free HeiGIT/ORS account and server key | Verify account-specific quota and terms; exhaust budget into a useful unavailable state |
| Maps | Leaflet with a policy-compliant configurable basemap | OSM attribution, normal browser referrer/cache behavior, no bulk/offline tiles; text/geometry fallback if tiles fail |
| Material source | Reviewed local source records linked to official EPDs | Record field-level QA and public-use rights; no assumed unlimited database/API permission |
| Data expansion | Bounded official ÖKOBAUDAT export/import | Inspect actual current format/license; generic datasets remain generic, not product EPDs |
| Storage | SQLite plus existing owned disk/backup capacity | Size/retention budget and restore evidence; no hosted DB dependency |
| Reports | HTML print and JSON export | Browser Print to PDF; no paid PDF SaaS |
| Monitoring | Existing structured logs, health, app-scoped metrics and maintenance | No new hosted telemetry subscription or collection of precise addresses |

[GitHub's billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-packages) distinguishes currently free Container registry storage/bandwidth from other private package/Actions artifact allowances. The inspected standalone guide's blanket statement about private-image storage needs this qualification. Self-hosting does not itself make every Actions storage feature free. Check current account budgets and avoid optional storage consumers.

[OSM tile policy](https://operations.osmfoundation.org/policies/tiles/) requires attribution, browser referrer, caching and no bulk/offline prefetch. Keep `strict-origin-when-cross-origin` or another compliant policy; an unconditional `no-referrer` security change would conflict. No service worker may precache public tiles. Offline fixture view uses a local schematic/table, not downloaded OSM map areas.

The map also needs an explicit CSP review: allow only selected tile origins in `img-src`, required same-origin/blob behavior if actually used, and Leaflet styling behavior. Test real browser console output. Keep script policy strict and avoid broad wildcards or `unsafe-inline` scripts. Document any narrowly required style-policy allowance and its reason.

[ÖKOBAUDAT data-user guidance](https://www.oekobaudat.de/en/guidance/data-users.html) permits attributed free distribution of unmodified data and distinguishes generic and EPD datasets. Retain originals, attribution and transformation lineage; do not claim a normalized derivative has unchanged official approval. Neither this review nor public PDF availability proves all EPD Danmark redistribution rights.

## 10. Execution protocol for a less capable agent

### Before every packet

1. Read current `AGENTS.md`, this plan's ledger, current packet and its dependencies. Recheck actual repository, branch, remote, dirty files, open PRs and run ownership.
2. Work in the **CarbonCalculator repository after P02**. Do not implement the product in the template or change Portfolio. A template defect gets a separate upstream PR after its downstream fix is isolated.
3. Claim one packet and concrete files. Use a dedicated branch/worktree. Preserve other sessions' work; do not stash/reset it or assume an old worktree is abandoned.
4. Confirm prerequisite outputs exist. Proposed paths/commands in this plan are not proof. Resolve missing foundational behavior before layering new features on top.

### Definition of done for every implementation packet

1. Complete its user-visible behavior across backend, generated contract, React, domain/persistence, errors, tests and docs that apply. Small dependent PRs are allowed; the slice stays incomplete until all parts work together.
2. Update corresponding audit rules and local-gate callers when behavior/paths change. Replace obsolete requirements with the new invariant. Never delete the audit merely to pass.
3. Run the actual downstream local gate **before pushing**. During the template stage use [docs/Test.md](../docs/Test.md#local-gate). Keep .NET builds/tests sequential in one checkout. Include React install/typecheck/lint/API drift/tests/build and meaningful feature/API/browser checks.
4. Stage explicit files; review complete diff and `git diff --check`; open a small PR with concrete behavior and validation. Require `build-test-push` green on its exact final head; recheck head after any change and before merging. Retarget dependent PRs before deleting their base branch.
5. Merge through GitHub, fetch, verify integrated content and successful exact-main CI/publication for code/configuration. Record source/head/merge/full SHAs and run URLs. A PR build is not a deployable release.
6. Update ledger with evidence, failures, decision changes, next exact action and remaining owner inputs. Do not assert a test/deployment succeeded merely because a script was generated.
7. Close finished task worktrees/branches after content verification, untracked/ignored review and dependency checks. Preserve primary checkout, private inputs, useful evidence and live task owners. Record deleted branch full SHAs in the linked PR or plan.

Ordinary Markdown-only retained changes use the repository's docs exception: review diff, `git diff --check`, PR, `[skip ci]` commit and squash title, then verify integrated `origin/main` content. Documentation under `docs/` or `Deployment/` still needs the applicable audit. A mixed PR uses the full gate. Respect actual protection; never weaken it or fake a check.

Initial import into a genuinely empty repository follows the existing [standalone product guide](../docs/StandaloneProduct.md) and Portfolio's documented initial-import precedent: no downstream PR base exists yet. A small locally gated seed configuration can accompany that first import with Actions disabled. Record pristine upstream SHA and seed delta separately. Every subsequent retained change uses a PR. If destination has gained any work, use a reconciled PR instead of the empty-repo procedure.

## 11. Dependency map and vertical delivery boundaries

| Slice | Packets | Visible outcome | Depends on |
| --- | --- | --- | --- |
| VS0 — Independent product | P01–P08; design work D01 | Safe own repo, React/LocalSingleNode only, meaningful CI and native capacity | Owner source/target intent |
| VS1 — Explore a real route | P09–P10 | Confirm new places, live HGV polyline/km/time, honest errors, usable map/table | VS0 and provider key for live acceptance |
| VS2 — Explain a material shipment | P11–P12 | Timber production/freight split, provenance drawer, immutable private report | VS1; reviewed timber source |
| VS3 — Five useful materials | P13–P14 | All five scenarios, missing-info recovery, warehouse ledger and load checks | VS2 |
| VS4 — Compare plausible corridors | P15–P16 | Reviewed live ferry approaches, deterministic recommendation/sensitivity and override | VS1; can research during VS2/VS3 |
| VS5 — Add reviewed data without rewriting UI | P17 | Staged importer and second-provider dataset through same use case | VS3 and source/format evidence |
| VS6 — Launch and sustain | P18–P21 | Native/private release, public HTTPS, acceptance, update/rollback/restore and handover | All required product slices, chosen design and operator access |

D01 precedes final visual component work. P01/P02 preparation and source reviews can proceed while design choice is pending. P03 may move early for CI capacity. Terminal/source research can begin immediately; missing keys do not block pure domain, importer or design work. Do not create horizontal “all backend, then all frontend, then test everything” phases.

## 12. Ordered granular packets

### D01 — Design choice and implementation brief

Inputs: section 3 and the three prepared previews.

1. Review A/B/C with the owner, including at least one phone layout and one explanation drawer. Capture choice and requested differences; do not infer approval from silence.
2. Refine selected empty/form/result/error/report views. Include no-key, quota, metadata-only EPD, stale result, no map and no clear preference states.
3. Record spacing/type/color/focus/status tokens, component inventory and mobile behavior. Show production and freight as separate indicators.
4. Copy selected design artifacts into the downstream repo when available; exclude mockup scripts and invented sample activity from runtime.

Exit: recorded owner direction plus a concrete UI brief. Foundation/source packets remain independent.

### P01 — Recheck baseline and execution prerequisites

1. Fetch template main and inspect open PRs, especially #290. Require successful CI on the chosen source SHA; record it and pinned .NET/Node/npm versions.
2. Read current standalone, React-only and single-node-only guides. Verify React host, generated contracts, release provenance, SSH/public setup and initial-import behavior in code.
3. Inspect CarbonCalculator visibility, emptiness, permissions and Actions. If nonempty, stop the import path and reconcile destination work through a PR.
4. Inspect account budget/limits and release storage behavior. Prefer merged, verified #290 if available. If still open, record the actual missing transport as a dependency; do not cherry-pick another agent's unmerged work silently or call it merged.
5. Recheck the intended existing node and runner scope using safe read-only APIs/private settings. Record shared apps and ownership boundaries without exposing secrets.
6. Preserve source manifest, previews and private operator facts for the downstream handoff. Do not commit machine paths/IPs or credential files.

Exit: reproducible source SHA, evidence-backed dependencies and a safe import/CI route.

### P02 — Seed the independent private repository

1. Disable destination Actions before copying workflows. Inspect whether a sibling `CarbonCalculator` checkout exists; preserve it if it has work.
2. Clone template history at P01's verified commit. Rename template remote to `upstream`; set `origin` to the exact supplied private CarbonCalculator repository.
3. Immediately set `gh repo set-default Grumlebob/CarbonCalculator`; use explicit `--repo` on consequential GitHub commands. Verify `gh` does not target the template by remote preference.
4. Prepare only the initial identity/profile delta: `React`, app slug/identity `carboncalculator`, image `ghcr.io/grumlebob/carboncalculator`, migration identity `carboncalculator-migrate`, `DEPLOY_TARGETS=localsinglenode`, and collision-safe private settings. Keep project folders until P06.
5. Remove inherited cross-profile publication from active seed configuration or ensure it cannot publish/start another profile. Align temporary target identity reads so no tool can act as `books` on the shared owner/node.
6. Run the inherited local gate for this seed, record pristine SHA/diff, then perform the one initial main push under section 10's empty-repository rule. No automatic CD/public exposure.
7. Copy this plan and the source bundle with its hash manifest into downstream planning/data-intake storage. Keep private source material private until rights review. Record source provenance/license; retain upstream history and LICENSE.
8. Keep Actions disabled until P03 establishes eligible capacity and routing variables. If identity is not safe, do not bootstrap using inherited defaults.

Exit: independent private repository and local checkout, safe product identity, retained history, unchanged template and no unintended publish/deploy.

### P03 — Establish CI on the existing node without taking its runner away

1. Confirm current runner owner/scope, labels, service paths and busy state. The observed personal-repository registration cannot be reused across repositories; see [GitHub runner scope](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners).
2. Reuse an already eligible CarbonCalculator registration if it now exists. Otherwise use the owner's 2026-10-15 approval for an additional CarbonCalculator-specific registration on the same machine. Do not ask for this decision again. Do not remove/re-register the template runner or move the repositories to an organization as an implicit workaround.
3. Use the retained native AgentSetup state machine from the CarbonCalculator checkout for app-specific runner/bootstrap work. The controller is Windows; do not run node setup here or in WSL. Confirm native hostname/address and preserve the existing hostname.
4. Only the node's explicit setup instruction triggers the native runbook. Follow its returned `agent` actions; the operator performs any returned `human` root command. If there is no CI yet, use its documented capacity-first sequence rather than requiring impossible first PR CI.
5. Set product-specific `CI_RUNNER_LABEL`, `CI_RUNNER_HOST`, `LOCALSINGLENODE_RUNNER_LABEL` and allowed target settings before enabling Actions. Confirm both CI and CD route to the expected repository/node.
6. Inspect disk/memory/Docker capacity and cross-repository build concurrency. Keep the shared deploy lock name/semantics; isolate per-job registry credentials and resources. Add scheduling/limits only through supported scripts and a reviewed change when evidence requires them.
7. Enable Actions; obtain successful product main CI. Preserve its run ID when watching is interrupted. Fix genuine failures through PRs; never rerun blindly or substitute a template run.
8. Establish controller SSH using the retained trust/pairing workflow if access is missing. Existing verified access can be used; no routine request for the owner to copy files or diagnose scripts.

Exit: CarbonCalculator jobs run on eligible capacity; existing runner/apps continue operating; first product main release evidence exists. Node setup alone is not public launch.

### P04 — Remove Blazor as a complete change

1. Follow [ReactOnlyClone.md](../docs/Frontend/ReactOnlyClone.md); inventory every active client/Razor/profile/build/test dependency before deletion.
2. Move browser tools/shared assets still used by React/tests out of the client. Keep the generated API command functional.
3. Remove `.Client`, host Razor/account UI, Blazor composition, WASM dependencies/assets and obsolete styles. Narrow Docker, MSBuild, local scripts and CI to React.
4. Remove the same-repository second-profile instance mechanism, its workflow inputs/docs and unsupported profile pairs. Preserve primary app identity/ownership checks.
5. Replace architecture/hosting/audit rules and fixtures with React-only assertions. Remove the old Razor Tailwind regeneration instruction from downstream AGENTS.
6. Run local/CI/image checks and inspect production output for no Blazor runtime or `_framework` payload.

Exit: one React frontend and C# host; no remaining build/deploy path accepts a Blazor release.

### P05 — Keep LocalSingleNode and relocate shared checks

1. Follow [SingleNodeOnlyClone.md](../Deployment/LocalSingleNode/SingleNodeOnlyClone.md); produce a keep/move/delete inventory with every live caller.
2. Move the reusable audit, render validators, Ansible installer, smoke helpers, library/tests and shared settings out of LocalCluster before deleting it. Proposed canonical audit is `Deployment/Common/Scripts/audit-deployment.sh`; prove the actual retained path.
3. Update CI, local gates, imports, tests and docs together. Replace cluster/cloud assertions with supported single-node/ownership/provenance rules.
4. Delete Cloud/LocalCluster targets, workflows, target maintenance and unsupported settings. Keep Common release, shared lock, Caddy, Cloudflare connector, backup and runner machinery used by LocalSingleNode.
5. Fail closed for removed deployment targets. Never rename the shared deployment lock just because its historical name contains `localcluster`.
6. Run retained audits/script tests/render/lint and full local/PR/main gates. No live host resource is removed by repository cleanup.

Exit: neither removed target directory has active callers; LocalSingleNode setup/deploy/maintenance/publication remains verifiable. Cloudflare Tunnel stays: it is the public connector, not the deleted Cloud deployment target.

### P06 — Rename surviving projects and release identity

1. Prepare an explicit rename map: `CarbonCalculator.sln`, host `CarbonCalculator`, `.Core`, `.Test`, `.React`, npm `carbon-calculator-react`, product image/migration identity and `com.carboncalculator.*` image labels.
2. Update namespaces/project references, assemblies/resources, solution, reflection/friend assemblies, Docker contexts/stages, Compose, launch tooling, test/report paths, API generation and Linux case-sensitive imports.
3. Update manifest writer/validator, image labels, release verification, smoke tests and audit atomically. Preserve source SHA/digest/run/attempt/repository/profile binding.
4. Update Dependabot, ignore/attribute rules, observability selectors/readiness user agent, coverage paths and maintained developer tools. Do not rename foreign/shared host infrastructure.
5. Run API generation drift check; the rename alone should not change the public schema. Classify every old-name match as historical provenance, intentional shared name or defect.

Exit: operational commands use CarbonCalculator names; Linux builds/publishes/releases work with coherent identity.

### P07 — Turn template documentation into product documentation

1. Rewrite README, requirements, local development, architecture, testing and operations around CarbonCalculator.
2. Remove inherited template plans/support files, fork/clone instructions and unused quality/tooling docs after extracting useful operational knowledge. Keep this product plan and `Plans/README.md`.
3. Preserve current LocalSingleNode/public/SSH/maintenance runbooks; remove setup-a-fork language from the finished product. Update audits that previously read deleted guides in the same packet.
4. Keep upstream attribution/license and a compact source-baseline record. Do not blanket-replace historical URLs.
5. Add the product favicon and honest page metadata. Keep private inputs out of docs and source archives.

Exit: a new contributor sees one production product and current commands, with no instruction to recreate removed template features.

### P08 — Install the product shell and acceptance contract

1. Add chosen design tokens/layout, route modules, accessible navigation and safe loading/error boundaries. Keep calculator placeholders clearly incomplete until VS1/VS2 land.
2. Remove route prerendering; verify ASP.NET SPA shell, known deep links, GET/HEAD behavior, asset caching and reserved-path denial. Do not return HTML for missing API/assets.
3. Define `React/CarbonCalculatorPublicV1` across resolver, manifest, labels, CI smoke, native setup/readiness and `Scripts/Test-DeployedSite.ps1`. Add a truthful capabilities/safe catalog probe, then expand acceptance as slices land.
4. Do not retain Books as the final acceptance target or reduce acceptance to HTTP 200. Until product checks exist, call the shell incomplete and keep public launch gated.
5. Verify React build output and strict CSP; select map dependency versions after compatibility review, not `latest` scaffold commands.

Exit: product routes and release pairing work; acceptance explicitly detects missing product behavior. **Checkpoint C1** becomes eligible when VS0 and D01's required implementation brief are verified.

### P09 — Source intake and real provider adapter through a thin slice

1. Import source data into versioned `Data/` locations with original SHA-256 manifest. Validate JSON shape, unique IDs, all references, unit/indicator compatibility, dates, variants and explicit metadata-only records.
2. Recheck timber PDF density/declared unit/indicators and rights status; record field-level page/table evidence. Other numeric records remain staged until P13 completes their review.
3. Add safe capabilities endpoint/configuration binding and server-only provider secret. No key means live unavailable, not fixture routing.
4. Implement typed Pelias search and HGV direction adapters with timeout, bounded errors, cancellation and exact coordinate/restriction mapping. Capture sanitized request digest/provider timestamp in integration evidence.
5. Add bounded cache, server/global quota counters and request validation before exposing expensive endpoints. Initial UI can use place search on submit.
6. Test actual adapter/request behavior with recorded sanitized responses and failure cases. Run one bounded real provider smoke once a key is available; do not equate fixture tests with this gate.

Exit: new place search and live HGV responses are reachable through product API, with no exposed key; first caller UI is completed immediately in P10.

### P10 — Complete VS1: Route Explorer in the browser

1. Generate/commit the API contract and typed client. Build confirmed from/to selection, swap, vehicle settings and optional via controls.
2. Submit explicit live route search and display real road geometry, km/time, source timestamp, vehicle assumptions and text-equivalent route details. No material/EPD is required.
3. Integrate lazy map, compliant attribution/CSP and a readable no-tiles/offline schematic fallback. A tile failure must not erase the numeric route result.
4. Handle no key, invalid key, ambiguous search, no route, malformed geometry, quota, timeout and cancellation. Prevent a late old response overwriting a newer search.
5. Mark results stale when routing inputs change; clear selected coordinates when their search label is edited. Back/Forward and deep-link refresh preserve predictable safe state without putting private inputs in URLs.
6. Prove Berlin→Odense then Berlin→Aarhus change provider geometry/distance; use a third arbitrary pair not shipped as a fixture, subject to provider serviceability.
7. Add source-linked screenshot/network evidence. Deterministic CI uses the fixture adapter; a separate bounded live check records real provenance.

Exit: useful complete route exploration, exact-head/main gates and real integration evidence. If the key is unavailable, this slice's live gate remains pending while independent packets continue.

### P11 — Complete the first material calculation journey

1. Add reviewed timber catalog/search/match selection with explicit `Use as proxy` and `Continue transport only` actions. Separate production country from dispatch location.
2. Implement quantity normalization, vehicle-load checks, pure EPD/freight calculations and initial lifecycle ledger. Bind selected routes to the server-issued input fingerprint.
3. Add calculation endpoint/generated contract, then calculator form, production/freight cards, selected route and actual substituted formulas in the evidence drawer.
4. Preserve all four available timber GWP indicators, explain negative biogenic/total values, and show generic freight factors/load assumptions and sensitivity. Keep the demo's 0.080 arithmetic; explicitly disclose its load mismatch and show 0.101 sensitivity. Production results remain indicative, not decision-grade.
5. Implement explicit demo selection using the supplied fixture. Display per-leg fixture status and offline schematic everywhere, including report/export metadata.
6. Test the actual C# engine through endpoint and browser against fixture goldens, quantity changes, no EPD, no quantity and stale result. Do not copy the handoff tests' private helper arithmetic as proof of production code.

Exit: timber from input through real route, separated impacts and explanations works end to end; offline case remains reproducible and visibly distinct.

### P12 — Immutable anonymous reports and persistent runtime transition

1. Add EF SQLite schema/migrations for route/cache envelopes, snapshot/capability hashes, expiry and persisted budgets. Treat catalog inputs as versioned files, not a public edit API.
2. Implement report access/deletion, token-safe client state, immutable read, JSON export/import and print layout. A report read/print/export must make zero provider calls.
3. Keep schema/method/catalog/factor/terminal/route revisions and original source values in each snapshot. Recalculate creates a new snapshot with an explicit comparison to the previous version.
4. Remove Books APIs/data and unused PostgreSQL/Redis/Identity/account/mail storage/services/secrets/migrations. Update dependency graph, local tooling, Docker, Compose, probes, operations, CI and audit together.
5. Update SQLite migration bundle/native dependencies, app volume ownership, doctor and backup/restore hooks. Do not deploy a PostgreSQL bundle against SQLite or pretend an empty/no-op artifact proves migration validation.
6. Prove wrong/missing token denial, expiry, deletion, XSS-safe import, size limits, report restart persistence and immutable results after catalog/factor changes. Verify logs and error responses contain no capability/key/address.

Exit: VS2 includes private reproducible reports and a product-owned persistent runtime, with no inherited sample/account database dependency. **Checkpoint C2** is eligible after this slice's merged/main evidence and live route gate pass.

### P13 — Five material families through the same calculator

1. Independently review the remaining four numeric source records against the official PDFs, including declared units, variants, indicator rows, density and expiry. Resolve public-use rights or retain staged/unavailable status.
2. Preserve metadata-only rows; add taxonomy and English/Danish synonyms through data, not React `if` branches. Distinguish ready-mix/wall, RT247/other bricks and WD100/other grades.
3. Implement the five editable starter scenarios. Their locations are suggestions, not proven shipment origins; obtain new live routes rather than embed kilometres.
4. Show Thermocell density/packing uncertainty and WD100's distinct production-volume/freight-mass conversions. Add per-unit output and useful material-only/transport-only states.
5. Exercise all five cases through production engine, API, generated contract and shared UI, including metadata-only steel/board/CLT and unknown category.
6. Record source review evidence and any missing-rights/method conditions without relabelling pending data as approved.

Exit: five source-backed numeric scenarios and honest broader search. Every source is accessible from UI/report; adding a compatible reviewed record requires no new UI switch.

### P14 — Incomplete information, warehouse and load behavior

1. Translate handoff section 6's missing-information table into explicit domain result states: quantity unknown; density unknown; no EPD; no origin; country-only reference; supplier HQ; destination factory/unknown.
2. Add one optional known warehouse through two physical movements, correct product boundary attribution, and per-movement route selection/emissions. Do not add a synthetic direct third movement.
3. Show hypothetical upstream nodes only as unresolved or already included in selected A1–A3. Validate graph references, cycles/duplicates and lot conservation; do not infer an unknown company.
4. Complete 60 t splitting, volume-limited cargo, oversize/indivisible rejection and per-load restrictions/allocation explanation. Unknown packing remains a limitation, not an invented truck count.
5. Ensure edits invalidate only affected route/material calculations but mark the aggregate snapshot stale until coherent. Recompute through the server and save a new snapshot.
6. Add contract/browser acceptance for ledger counted/excluded rows, two-leg reports, missing-information recovery and no fabricated totals.

Exit: VS3 handles useful real incomplete cases and known intermediate transport without double counting.

### P15 — Review both ferry services and validate approaches

1. Inspect current official freight service instructions and access maps for Puttgarden, Rødby, Rostock and Gedser. Record entry/exit coordinates separately with source/revision and directional review.
2. Verify accompanied-truck availability and dated sailing reference values. Sea km/geometry remain a labelled reference/schematic, not current vessel telemetry.
3. Run bounded actual HGV approach and exit tests for every enabled direction, with proper laden restrictions, maximum snap-gap checks and no hidden road-ferry sections.
4. Keep failed/unverified directions disabled with actionable reason codes. Do not replace a failed gate with a town centre. Seek missing source evidence only if agent research cannot resolve it.
5. Update registry approval workflow, schema validation and source evidence. Store sanitized response/request hashes and directional approvals.

Exit: both services have evidence-backed directions ready for route generation. Incomplete terminal evidence remains a real inference blocker; live road-only remains useful.

### P16 — Complete VS4: unknown-route comparison and sensitivity

1. Implement section 7's candidate generator with geographic prefilter, per-leg provenance, bounded call budget, failures/exclusions, feasibility/deduplication and explicit require/avoid constraints.
2. Add pure stable ranking, ambiguity, 15/45/90 min waiting sensitivity and factor sensitivity. No invented probabilities, freight prices or timetable promises.
3. Integrate cards/map/table selection, `Why this route?`, user override and separate carbon comparison. Keep incomplete routes out of comparable totals.
4. Compare road versus live-road-plus-reference-ferry candidates for a suitable new query and both crossings/directions where relevant. Include a within-Jutland case that does not force a ferry.
5. Verify partial provider failure leaves remaining complete candidates honest, and changing user constraints cannot silently choose a forbidden corridor.
6. Prove fixture 45/90 min behavior through the same ranking engine and UI. Save full candidate/exclusion/provenance/sensitivity data in report snapshots.

Exit: actual live road approaches support explainable corridor inference; fixture-only comparisons do not pass this slice.

### P17 — Staged catalog tooling and bounded ÖKOBAUDAT integration

1. Implement a local/admin CLI, proposed `dotnet run --project CarbonCalculator.DataTool -- validate <path>` and `... -- import-oekobaudat --file <official-export> --limit 50 --output <staging-dir>`. Add help and test it before documenting it as executable.
2. Inspect a real current official download/schema. If it is not the handoff's assumed flat CSV, implement the actual documented format with a mapping ADR; never assign columns by position or invent an A1–A3 fossil field.
3. Validate record UUID/version, provider, generic/product-EPD classification, standard/method/modules, units, geography, dates, numeric notation and rights. Bound archive expansion/rows/depth and reject unsafe paths/files.
4. Produce a staging summary: read, rejected, metadata-only, needs-review, numeric-approved. Approval is an explicit reviewed change, not automatic extraction success.
5. Promote one suitable German dataset with field-level source QA, original hash/attribution and normalized revision. Query/select it through the same catalog/API/UI and calculate only approved compatible indicators.
6. Prove rollback/re-import idempotence, no record-ID collisions and unchanged old reports. Add “how to add a record/provider” docs with a real worked example.

Exit: reviewed second-provider data works end to end without a new screen-specific calculator or public administration/upload endpoint.

### P18 — Release readiness and final production acceptance

1. Review all handoff T01–T30, R1–R7 and V3-01–V3-24 acceptance IDs against implemented tests/evidence; read the original list rather than reconstructing it from memory. Record gaps, never silently delete an ID.
2. Finish `CarbonCalculatorPublicV1` acceptance with safe catalog/capability checks, deterministic five-material/route/ledger/report journey, reserved-route denial and release/data/method identity.
3. Keep live integration checks separate and bounded. CI mock-provider success does not prove HeiGIT access; public readiness does not require spending a route call every health check.
4. Review session/report privacy, retention, log redaction, proxy trust, provider budget, source rights and public notices using actual behavior. Verify no routing key in JS/source maps/image metadata.
5. Review chosen UI across device sizes, keyboard/contrast/focus/reflow/reduced-motion and map alternatives. Test print at A4 with long sources; no clipped formulas/units or missing footer caveats.
6. Perform the handoff's five-beginner evaluation: at least four correctly distinguish making/moving and modelled/actual after self-guided use. The agent can prepare tasks and record feedback; genuine human participants cannot be replaced by invented answers. Recruit through the owner only when external participants are actually needed.
7. Measure production bundle, lazy map loading and representative mobile performance; record conditions. Initial goals: LCP ≤2.5 s and CLS ≤0.1 where meaningful; do not equate lab scores with field data or set a 100 Lighthouse score as release proof.
8. Produce exact-main successful release manifest, image/payload digest, source SHA, run/attempt, React/acceptance pair and method/data revision. Record SQLite schema compatibility and bounded storage/evidence policy.

Exit: all mandatory slices and release checks have actual evidence; only native/public execution remains. **Checkpoint C3** is eligible here.

### P19 — Native app installation and LAN acceptance

1. Recheck operator authorization, intended existing native node and CarbonCalculator ownership. Inspect prior P03 setup state; do not rerun first bootstrap or rename the host by habit.
2. Run app-scoped collision/doctor checks. Choose free ports/subnet/runtime/backup roots through private settings. Preserve other apps' containers, volumes, Caddy sites, tunnels, runner service and shared lock.
3. Verify final migration/database/backup settings and server-only key provisioning. The owner supplies only authentication material unavailable through existing protected access.
4. Select the published P18 source/digest and dispatch one authorized LocalSingleNode deployment from verified main, using actual documented inputs. Record the run ID immediately; resume observation of that run after interruption.
5. Require manifest/payload/image verification before migration, product acceptance after start, and controller-independent LAN/browser checks against `CarbonCalculatorPublicV1`.
6. Verify persistence across app restart and report/token rules; confirm unrelated existing applications still respond and their identities/resources were not changed.

Exit: correct product release works on LAN on the existing shared node. No controller or WSL node bootstrap.

### P20 — Publish the requested hostname and accept the live product

1. Use retained LocalSingleNode PublicSetup with protected controller authentication and private ownership state. Reuse valid access; ask only for an unavailable credential/login action.
2. Inspect DNS/tunnel ownership for the requested hostname. Reconcile only provably owned resources; refuse a conflicting foreign record. Create CarbonCalculator's dedicated tunnel/connector/loopback-origin site through scripts.
3. Configure repository public variables/connector secret through the existing encrypted input flow. Do not copy another application's tunnel token or alter zone-wide bot/cache settings.
4. Run the authorized deployment/publication path for the exact published release. No deploy of the current docs-only main without specifying a previously published target SHA or producing a fresh successful publication.
5. Independently verify HTTPS certificate, DNS/connector health, deep links, API/catalog, map attribution/console, five materials, bounded real route/ferry check, source drawers, report access denial and print/export.
6. Use the implemented acceptance command, proposed final form: `pwsh -NoProfile -File Scripts/Test-DeployedSite.ps1 -FrontendProfile React -AcceptanceProfile CarbonCalculatorPublicV1 -BaseUrl https://carboncalculator.jacobgrum.com`.
7. Record public evidence and actual release/data/method identity. Test that precise report/address content is not cached at the edge. Keep shared Cloudflare settings unchanged unless the owner authorizes a separate concrete change.

Exit: intended HTTPS product passes external acceptance; a DNS record, screenshot or HTTP 200 alone is insufficient.

### P21 — Recovery, maintenance, handover and cleanup

1. Publish a small compatible update through PR/local gate/exact-head CI/green main, deploy it, and prove expected behavior/identity.
2. Roll back to a compatible prior image through retained scoped scripts and verify product/data identity; roll forward again. A code rollback does not undo an incompatible SQLite migration. Use expand/contract migrations or a reviewed restore procedure.
3. Prove app restart and dedicated connector restart recovery without disturbing other apps. Do not reboot a shared node by default; only do so for an authorized concrete recovery concern.
4. Create a consistent SQLite backup and restore it into an isolated owned test target. Verify schema/data/snapshot content and capabilities/expiry behavior without publishing or overwriting the production DB. Record checksum and restore evidence, not just backup-file existence.
5. Document app-scoped doctor, logs, budget exhaustion, secret rotation, source updates, catalog approval/import, retention, report expiry, backup/restore and compatible rollback. Use real commands from implemented tooling.
6. Reconcile every required acceptance ID and pending owner question. Record explicit owner deferrals; a unilateral smaller release is not whole-plan completion.
7. Fetch/prune, verify integrated content and no task/PR/process/lock dependency, then remove finished worktrees and local/remote branches. Record full deleted branch SHAs. Archive only unique necessary evidence/notes outside removed checkouts with verified SHA-256; never whole checkouts/build output.
8. Leave the primary CarbonCalculator checkout and main branch, private configuration and useful source/design evidence. Retain another task's worktree only with its concrete owner/dependency recorded.

Exit: public product, update/recovery/data-restore evidence, maintainable documentation, complete ledger and verified workspace closeout.

## 13. Acceptance matrix and anti-shortcut checks

| Area | Required evidence | Common false completion to reject |
| --- | --- | --- |
| Repo independence | Private destination, preserved baseline history, own image/app/release identity | Renaming a folder while `gh`/CD still targets template |
| Product cleanup | Active-reference inventory, replacement audit rules, React-only image and single-node workflows | Deleting directories while CI imports LocalCluster |
| Live routes | New query through actual browser/API, server provider timestamp/request hash, changed geometry | Same Hamburg fixture returned for arbitrary addresses |
| EPD values | Official row/page/variant review and actual engine/API/browser result for all five | Supplied test helper passes, production code untested |
| Incomplete knowledge | Per-unit/no-route/transport-only states with explicit assumptions | Unknown becomes zero or headquarters becomes factory |
| Loads | Weight/volume allocation and correct per-load gross routing restrictions | 60 t routed as one vehicle or cargo multiplied twice |
| Ferry inference | Directional terminal review, live approaches, reference sea leg, ranking/sensitivity | Harbour centroid + static road km labelled live |
| Boundaries | Ledger tests, replacement A4, upstream exclusion, no mixed-method total | Negative timber total cancels freight in a headline |
| Reports | Immutable snapshots, capability denial, expiry/delete/export/import and no reread provider calls | Guessable public report lookup or silent recomputation |
| Quota/free-only | Account allowance evidence, global persisted budget, no unexpected retries/artifact spend | Self-hosted CI assumed to make all storage free |
| Expansion | Real bounded staged ÖKOBAUDAT import, reviewed result through same UI | An empty adapter class advertised as integration |
| UX | Chosen design, responsive/keyboard/print checks and actual beginner feedback | Generated mockup screenshot used as app evidence |
| Delivery | Exact-head CI, exact-main publication, digest/profile/revision and LAN/public browser acceptance | Green PR or DNS setup treated as live deployment |
| Recovery | Compatible rollback/forward and isolated consistent SQLite restore | A backup file exists but has never been restored |

Keep source acceptance IDs in a downstream `Acceptance.md` ledger with columns: original ID, packet, test/artifact path, last evidence, status and reason. Values are `pending`, `passed`, `blocked` or `owner-deferred`; never make “not applicable” a quiet scope deletion.

## 14. Operator dependencies and genuine manual work

These are dependencies of later execution, not reasons to stop planning. Reuse existing authenticated access and safely automate everything else.

| Input/action | Current state | Agent work first | Human involvement only when required |
| --- | --- | --- | --- |
| Visual direction | A/B/C prepared; no selection | Provide previews and recommendation | Owner chooses direction or requested combination |
| Runner interpretation | Additional CarbonCalculator registration approved on 2026-10-15; preserve current template runner | Verify current scope and prepare supported same-node setup when execution starts | No further confirmation of the registration choice is needed; any returned native human step still applies |
| Native privileged setup | New app-specific runner/bootstrap is likely | Prepare checkout/identity and native status result | Run the exact `human` root command returned by the native runbook; never give a speculative sudo command now |
| HeiGIT account/key | No key used by this planning task | Check protected existing configuration by presence only; implement adapter/tests/quota controls | If absent, owner registers/verifies a free account and enters the key through protected secret input, never chat |
| Cloudflare authentication | Existing access not inspected for this product | Inspect usable protected controller access and owned DNS/tunnel | Only missing login/scoped credential authorization; agent creates/configures resources |
| EPD/terminal evidence | Source links exist; publication/directional review pending | Inspect official sources, policy evidence and live approach tests | Ask for rights clarification or unavailable source evidence only after research cannot resolve it |
| Beginner evaluation | No participants tested | Prepare short tasks, build usable product, record feedback format | Genuine participants or owner-provided feedback are required; five invented AI personas do not pass |

Do not tell the owner to manually create the repository, clone code, write configuration, build the app, create DNS/tunnels, upload ordinary files, generate OpenAPI, run routine tests or diagnose scripts. Those are agent tasks when authorized access exists.

No root action is run from this controller chat. The native [AgentSetup.md](../Deployment/LocalSingleNode/AgentSetup.md) explicitly assigns its returned human step to the operator: **“The operator authenticates and runs the one root command.”** This is a runbook constraint, not a blanket requirement for human approval of every remote action.

Do not claim existing Cloudflare authentication or keys are missing without checking through safe protected access during execution. Do not ask for paid plans, regulator certification or a specialist appointment to publish an honestly qualified scenario tool. Formal/compliance claims and paid-service adoption are separate future scope.

## 15. Progress ledger, evidence and fresh-chat handoff

The downstream copy becomes authoritative after P02. Keep a compact current checkpoint at the top of this document or a linked product-only `Plans/Support/CarbonCalculator/Progress.md`; do not retain two competing execution ledgers.

Initial checkpoint:

```text
Authoritative repository: template for planning; CarbonCalculator after P02
Current packet: planning delivered; implementation not started
Next action: review accessible mockups; design and launch timing remain pending;
  additional same-node CarbonCalculator runner registration is approved
Completed preparation: source copy + SHA-256 manifest, 23 supplied tests,
  template/runner/remote inspection, three local responsive design previews
Pending mandatory evidence: all product packets, live key/provider checks,
  source publication review, terminal approaches, public/recovery acceptance
Live authorization: none transferred from Portfolio/template
```

Each packet record contains:

```text
Packet / owner / state:
Repository, branch/worktree, base full SHA, claimed files:
Prerequisite evidence and owner decision references:
Implemented behavior and documented deviations:
Local checks and result evidence:
PR URL / exact head / required check run:
Integrated full SHA / exact-main CI and publishing run:
Release image + payload digest / run attempt / schema/data/method revision:
Deployment run and authorization reference, if applicable:
Public/LAN acceptance, if applicable:
Remaining input/blocker and independent next work:
Next packet and first concrete command/action:
Deleted branch name + full SHA; retained worktree dependency:
```

Recommend fresh chats at C1 foundation, C2 first report journey and C3 release readiness. Finish verified integration boundaries first. A fresh chat is optional; it does not pause an active goal, permit redoing bootstrap or complete unfinished scope.

Use this filled continuation structure at a checkpoint:

```text
Continue CarbonCalculator from Plans/CarbonCalculatorDelivery.md and its
authoritative progress ledger. Work only in the recorded product checkout.
Read AGENTS.md. Recheck dirty files, ownership, remotes, open PRs and run IDs.
Last verified boundary: <slice, full SHA, exact-main CI, evidence>.
Current claim: <packet/files/owner or none>.
Next task: <packet and first unfinished substep>.
Design decision: <owner choice and brief>.
Private inputs: <locations only; never paste credentials>.
Live authorization: <exact scope/reference or not yet authorized>.
Missing inputs and independent work: <specific items>.
Do not recreate finished setup, copy another app's identity, dispatch a duplicate
run, waive required CI, replace live routes with fixtures, or drop required scope.
Complete checks/integration/evidence/closeout for each packet before advancing.
```

## 16. Open product decisions

Only these choices warrant asking now; technical defaults elsewhere are already specified:

1. **Visual direction:** Fieldwork A, Route Desk B, Material Ledger C, or a concrete combination. Recommended A with B's richer route inspector added later.
2. **Public launch level:** after reviewing the mockups, decide whether to launch a clearly labelled road-only beta as soon as it is safe and useful, or wait for complete v1 ferry comparison and second-provider import. The owner explicitly deferred this decision until mockup review; no launch option is approved yet. The early-beta recommendation does not reduce complete-v1 requirements.

Resolved: the owner approved a CarbonCalculator-specific runner registration on the existing node on 2026-10-15, preserving its current runner. Do not ask this question again.

No need to ask the owner to select an ORM, state library, validation framework, API versioning pattern or deployment ports. Revisit a default only when evidence or a new product requirement makes it unsuitable.

## 17. Completion and planning closeout

The **planning task** is complete when this detailed plan is reviewed, integrated through a documentation PR and verified on template `origin/main`, local previews/source evidence are preserved outside its temporary task checkout, and questions/manual dependencies are reported. Record planning PR and integrated SHA in its PR description to avoid a self-referential verification commit.

The **implementation goal** is complete only when:

1. CarbonCalculator is independent, private, React/ASP.NET and LocalSingleNode-only; cleanup and actual downstream gates are complete.
2. All mandatory vertical slices have real evidence, including five materials, real routing, reviewed ferry inference, private immutable reports, warehouse/load/boundary behavior and bounded second-provider import.
3. The requested HTTPS product serves the verified immutable release with correct method/data revisions and passes independent public acceptance.
4. Free-only operation, scoped shared-node ownership, update/compatible rollback, consistent data restore and maintainable handover are proven.
5. Required work is complete or explicitly deferred by the owner with recorded reason; workspace cleanup and authoritative next-work notes are finished.

Never mark complete because the UI looks finished, CI passed somewhere, a provider key is missing, a token budget is ending, or a smaller milestone was deployed.
