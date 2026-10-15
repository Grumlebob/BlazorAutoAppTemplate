# CarbonCalculator acceptance and source traceability

Status: specification only, 2026-10-15. **Every implementation row below is pending.** Accepted mockups and the 23 supplied source-data tests do not pass these product gates. No product tests were run by this planning revision.

This ledger preserves all 30 T IDs, seven R IDs and 24 V3 IDs from the supplied handoff. Source: the SHA-256-preserved `Calculator.md` sections 22/33 and `docs/LIVE_ROUTING.md`. Copy the originals privately into downstream source intake during P02. [FeatureSpecification.md](FeatureSpecification.md) supersedes the handoff's framework and UI composition; [ImplementationPackets.md](ImplementationPackets.md) defines executable checkpoints.

Each row's proof is a proposed test/evidence target, not an existing test. During implementation add columns or linked records for exact test/artifact path, commit, run/time, result and reason. Valid states are pending, passed, blocked and owner-deferred. Do not substitute source fixture checks for production engine/API/browser evidence.

## 1. Test organization and proof levels

| Level | Target responsibility | What it cannot prove |
| --- | --- | --- |
| Domain | Actual C# quantity, matching, method, load, ledger, aggregation and ranking policies | Provider/network access or browser usability |
| API | Real application host, generated contracts, capability/validation, persistence, upstream adapter fixtures | Real upstream quota/key/service availability |
| Browser | Real ASP.NET/React app against deterministic providers and owned isolated data | Live provider success or five real humans' understanding |
| Live | Bounded explicit new geocode/HGV/terminal calls with sanitized evidence | Carrier history, exact manufacture or measured emissions |
| Release | Exact-main CI/publication, immutable identity, deployment/public/recovery | Completion of untested feature behavior |
| Human | Five genuine beginner sessions with unedited feedback | Formal standards certification or numerical audit |

Suggested test folders are `CarbonCalculator.Test/Domain`, `Features`, `Infrastructure` and `E2E`, plus source-intake verification and an ignored sanitized live-evidence directory. Reuse the template's actual testing stack; do not install a second browser framework because the source handoff named one.

## 2. Original T01–T30

| ID | Preserved requirement | Packet | Proposed proof target |
| --- | --- | --- | --- |
| T01 | 20 t timber / 488 kg/m³ gives 40.98360655737705 m³ | P11 | Domain QuantityConversion.TimberMassToVolume; API normalized units |
| T02 | 28.8 fossil per m³ gives 1,180.327868852459 kg | P11 | Domain EpdScaling.TimberFossil; browser separate production card |
| T03 | Timber total −728 per m³ gives −29,836.06557377049, without whole-life-negative claim | P11 | Domain EpdScaling.TimberTotal; browser indicator/caveat |
| T04 | Fixture road 20 × 515 × .080 = 824 WTW | P11 | Domain FreightFixture.Road; API result nodes |
| T05 | Fixture Puttgarden gives 550.24 WTW | P11, P16 | Domain FreightFixture.Puttgarden; browser selected legs |
| T06 | Fixture Rostock gives 680.224 WTW | P11, P16 | Domain FreightFixture.Rostock; API selected legs |
| T07 | Fixture effort 340/390/455 prefers Puttgarden | P16 | Domain Ranking.DefaultFixture; coherent map/table selection |
| T08 | 90-minute buffer produces no-clear-preference for 385 versus 390 | P16 | Domain Ranking.Ambiguity; browser sensitivity |
| T09 | .101 sensitivity gives 1,040.3 / 682.54 / 827.224 WTW | P11, P16 | Domain FreightFixture.FactorSensitivity; source labels |
| T10 | Changing Hamburg to Berlin invalidates route/fixture assumptions | P10, P11B | Browser InputInvalidation.ChangedOrigin; different live evidence |
| T11 | CLT metadata remains discoverable without numeric production | P13 | API Catalog.MetadataOnly; browser unavailable not zero |
| T12 | Sawn lumber cannot silently match CLT/glulam | P11, P13 | Domain Matching.ProductFamily; explicit proxy interaction |
| T13 | SW/FI source versus German manufacture retains geography warning | P11 | Domain Matching.Geography; UI/export warning code |
| T14 | Generic EPD A4 and replacement route are not both counted | P11, P14 | Domain Ledger.AlternativeA4; report exclusion row |
| T15 | Covered upstream log transport is informational, not additive | P14 | Domain Ledger.UpstreamIncluded; browser ledger |
| T16 | Dispatch–warehouse–site counts two movements and no direct third | P14 | Domain Ledger.Warehouse; API/browser movement IDs |
| T17 | Another factory/unknown transformation is unclassified, not automatic A4 | P14 | Domain Ledger.OtherFactory; blocked declared-stage total |
| T18 | 60 t / 25 t payload allocates 25/25/10, not one overloaded truck | P14 | Domain LoadAllocation.MultipleLoads; browser allocation |
| T19 | 20 t cargo + 15 t tare sends 35 t HGV restriction | P09, P11 | API HeiGitAdapter.GrossMassPayload; sanitized live request |
| T20 | Route override changes map/time/emissions/report coherently | P16 | Browser Selection.Override; snapshot selected ID |
| T21 | Provider failure never becomes a live-labelled fixture | P09–P10 | API ProviderFailure; browser explicit sample action |
| T22 | Valid mass/route without EPD yields freight, production unavailable | P11 | API Partial.TransportOnly; browser no zero production |
| T23 | No amount permits per-unit/per-1-tonne values, not a receipt total | P11, P11B | Domain Partial.UnknownQuantity; partial save/browser coverage |
| T24 | Company-only input does not silently route from legal HQ | P10 | Browser Places.CompanyHint; no confirmed dispatch |
| T25 | Irrelevant/infeasible ferries omitted or reasoned, never forced | P15–P16 | Domain Candidates.GeographicExclusion; browser exclusions |
| T26 | Lat/lon converts to provider/GeoJSON lon/lat correctly | P09 | Domain Coordinates; API outgoing payload/geometry |
| T27 | Negative/nonfinite amount and impossible truck fail validation | P11, P14 | API Validation.NumericAndVehicle; preserved edit buffer |
| T28 | Reopened report survives catalog/factor updates unchanged | P12 | API Reports.ImmutableAfterCatalogChange; print/JSON equality |
| T29 | 1 t versus 20 t scales linearly when allocation constraints unchanged | P11 | Domain Scaling.LinearCompatibleCase; no claim beyond assumptions |
| T30 | No mixed EPD GWP/WTW grand-total field | P11B, P12 | Contract/Domain Aggregation.NoMixedMethod; UI/export schema |

## 3. Original R1–R7 live-routing gates

The source's Node CLI examples are evidence helpers, not the product backend. Equivalent actual ASP.NET adapter smoke/CLI evidence is permitted when recorded as the implementation adaptation. Source scripts remain retained as reference; a helper's success alone does not pass the app's live journey.

| ID | Preserved requirement | Packet | Actual evidence required |
| --- | --- | --- | --- |
| R1 | Real HGV smoke succeeds and produces sanitized evidence | P09 | New upstream HTTP success, nonempty valid geometry, positive distance/duration, request hash/time/profile; no secret |
| R2 | App routes Hamburg–Copenhagen live, then Aarhus produces changed result | P10 | Real browser/API requests and changed coordinates/geometry/distances |
| R3 | New Berlin–Odense, Lübeck–Aarhus, Munich–Copenhagen handled honestly | P10, P16 | New searches; successful supported routes or genuine errors, relevant ferry prefilter |
| R4 | Invalid/expired key gives setup/error, not fake success | P09 | Safe live failure evidence, no fallback route mislabel |
| R5 | Every road leg avoids ferries; unapproved HGV gates unavailable | P15 | Outgoing request options and per-direction access evidence |
| R6 | Per-leg live-road/reference-ferry/assumption/fixture provenance | P10, P16 | Actual API, UI and snapshot source modes/timestamps |
| R7 | Report reproduces checked distances/source times; rerun gets new ID | P12 | Immutable read with no upstream calls and explicit new calculation |

## 4. Original V3-01–V3-24

| ID | Preserved requirement | Packet | Proposed proof target |
| --- | --- | --- | --- |
| V3-01 | Supplied offline verification passes; five usable EPDs across four families | P09, P13 | Source verification plus independent actual C# engine/catalog coverage |
| V3-02 | Actual upstream HGV HTTP response with positive geometry/time/distance | P09 | Live R1 evidence through real adapter, not mock HTTP |
| V3-03 | App default live Hamburg–Copenhagen, HGV/no-ferry road and city precision | P10 | Browser live route and outgoing payload/source timestamps |
| V3-04 | Aarhus changes request/geometry/distance; no fixed fixture reuse | P10 | Browser/API changed-input live evidence |
| V3-05 | Berlin–Odense and Munich–Copenhagen yield route or genuine service error | P10 | Sanitized new-query outcomes, no fabricated success |
| V3-06 | Missing key/network block shows routing unavailable and explicit sample | P09–P10 | API/browser failure variants and preserved inputs |
| V3-07 | Standalone route exploration works without material/EPD | P10 | Browser contextual Route Explorer, live result |
| V3-08 | Unknown route compares live approaches and sourced sea when gates approved | P15–P16 | Live directional approaches plus UI provisional alternatives |
| V3-09 | Unapproved gates leave ferry unavailable and multimodal gate incomplete | P15 | API/browser availability; ledger remains pending/blocked |
| V3-10 | SHT wall 12 t gives 1,812 fossil, not generic ready-mix | P13 | Domain/API/browser exact variant and official field citation |
| V3-11 | RT247 10 t gives 495 fossil; no RT248 substitution | P13 | Domain/API/browser variant match and mismatch |
| V3-12 | Thermocell 500 kg gives 478 fossil; no invented volume | P13 | Domain/API/browser density-range and packing state |
| V3-13 | WD100 15 m³ gives 792 fossil and 1.53 t cargo | P13 | Domain/API/browser separate units and grade |
| V3-14 | Timber 20 t gives 1,180.327868… fossil plus geography warning | P11 | Domain/API/browser reviewed density/impact/source fit |
| V3-15 | Steel/board metadata has no invented production stage | P13 | API/browser material unavailable with original source |
| V3-16 | Second known warehouse movement preserves ledger and separate emissions | P14 | Browser two movement edits and no direct third count |
| V3-17 | Unknown upstream supplier creates neither company nor extra A2 | P14 | Domain/API/browser unknown-node/exclusion behavior |
| V3-18 | Every value explanation shows actual source/page/formula/inputs/evidence | P11B, P16 | Calculation-node contract and browser/contextual report drawers |
| V3-19 | Downloaded report preserves live source/time/EPD fit/factor assumptions | P12 | Snapshot/print/JSON evidence and no mixed total |
| V3-20 | Four of five genuine beginners distinguish EPD/routing and estimated/actual | P18 | Human tasks, original feedback and counted outcomes |
| V3-21 | Puttgarden–Rødby truck gates versioned; both road approaches live | P15 | Official directional gate/snapping sources, two real road results, separate sea/per-leg arithmetic |
| V3-22 | New Berlin–Odense geocode and HGV route through actual provider | P09–P10 | Live search/selection/request evidence; any scripted first selection explicitly marked proxy |
| V3-23 | Active provider URLs use HeiGIT, not deprecated host | P09, P18 | Source/config/request audit; old-host strings permitted only as rejection tests/history |
| V3-24 | Metadata-only steel/gypsum still permits transport-only | P13 | Browser exact missing-production plus valid freight outcome |

## 5. Added product acceptance AC01–AC40

These additions close gaps between the source prototype and the approved construction-site product. They do not replace any original ID.

| ID | Required behavior | Packet | Proposed evidence |
| --- | --- | --- | --- |
| AC01 | Approved Fieldwork/direct-navigation design retained without another chooser | D01, P08 | Component brief and implementation screenshots |
| AC02 | Add delivery beside list; no To review card, duplicate list or review route | P08A, P11B | Browser Dashboard desktop/mobile/keyboard |
| AC03 | Material/Transport/Documents deep links target the same record directly | P08A | Router/direct refresh/Back/Forward and selected-section focus |
| AC04 | Section switching preserves dirty fields, attachments and route selection | P08A, P12A | Browser edit buffer across all sections and About |
| AC05 | Save survives browser close under approved D02; failed writes are not success | P08A | New page/browser profile behavior and quota/transaction failure |
| AC06 | Incomplete delivery saves with missing quantity/origin/EPD/provider | P08A, P11B | Browser partial-save/reopen and no numeric zero substitution |
| AC07 | Edit/save preserves stable ID without duplicate counting | P08A, P11B | Store transaction/revision tests and aggregate count |
| AC08 | Dirty leave offers Save/Discard/Stay; section switch needs no warning | P08A | Browser route/project navigation with unsaved fields |
| AC09 | Projects isolate records, documents, filters and destination edits | P08A, P12A | Two-project browser/API scope denial |
| AC10 | Two-tab conflict preserves both edits and never silently overwrites | P08A | IndexedDB revision/concurrent browser contexts |
| AC11 | Duplicate warning permits deliberate additional receipt/shared invoice | P11B | Same/different date/material/line cases |
| AC12 | Received date stays local calendar date across timezones | P08A | Store/export/import/date display around timezone boundaries |
| AC13 | Saved incomplete/stale records excluded from current aggregate with coverage | P11B | Domain/API/browser totals and filter link |
| AC14 | Search/paging filters rows without changing project-wide estimate | P11B | Browser all-project scope and 50-row paging |
| AC15 | Compatible standard sample lines total 193 with matching breakdown | P11A–P11B | Actual C# aggregate and UI source units |
| AC16 | Different methods/editions/quantity bases stay separate | P11B | Domain compatibility key and API/UI groups |
| AC17 | Standard method works without dispatch, EPD or routing key | P11A | API/browser missing-provider/origin cases |
| AC18 | Standard category/edition/received-versus-incorporated basis explicit | P11A | Eligibility/mapping/source revision and qualified receipt result |
| AC19 | Project additions are excluded, never multiplied once per delivery | P11A | Domain/API/print scope and no invented compliance total |
| AC20 | Input edit invalidates only dependent results; late request cannot overwrite | P11B | Fingerprint/request-race and contextual/numeric change matrix |
| AC21 | Unknown/forged/rebound local snapshots cannot enter verified current total | P11B, P12B | Signature/key-revision/replay/ID mapping cases |
| AC22 | Genuine complete zero differs from no estimate | P11B | Domain tagged values and UI empty/zero states |
| AC23 | Attach/preview-or-download/remove reachable directly from Dashboard | P12A | Browser real selected-file lifecycle |
| AC24 | Attachment never extracts quantity/dispatch or authenticates a fact | P12A | Browser input snapshots before/after attach |
| AC25 | Wrong/missing evidence capability and guessed IDs deny retrieval/deletion | P12A | API ownership and inaccessible response consistency |
| AC26 | File type/magic/size/count/image-pixel/global limits enforced | P12A | Hostile upload fixtures and bounded memory/disk outcomes |
| AC27 | Interrupted/retried upload is idempotent and leaves no accessible partial bytes | P12A | API cancel/restart/promotion/reconciliation cases |
| AC28 | Local original survives server expiry under D02; unavailable copies labelled | P12A | Clock-controlled expiry and browser local download |
| AC29 | Removed attachment stays historical metadata without leaking old access | P12A | Immutable snapshot plus deletion/expiry and no public URL |
| AC30 | Report JSON omits tokens/raw files and reproduces exact source values | P12 | Serialization/privacy and no-network read |
| AC31 | Project backup/import distinct from report and honest about absent originals | P12B | Fresh browser restore preview and originals manifest |
| AC32 | Hostile/duplicate/unsupported import cannot overwrite existing project | P12B | Transaction rollback, schema/URL/count/size and fresh-ID cases |
| AC33 | About owns general lessons; working forms retain specific source access | P08, P11B | Browser no teaching dropdown/card and accessible contextual drawer |
| AC34 | Quota and cache count each real provider leg/retry across restarts | P09, P18 | Persisted counters, concurrent dedupe and provider-call accounting |
| AC35 | No-key/offline/tiles failure preserves useful records/material/standard results | P10, P11A | Browser failure matrix; no fixture labelled live |
| AC36 | Public/private API, assets, deep links, CSP and caching behave correctly | P08, P18–P20 | Host/browser/public reserved paths and capability/content cache checks |
| AC37 | SQLite/documents/signing-key restore preserves signature/expiry/access behavior | P12, P21 | Isolated consistent restore, checksums and original expiry clock |
| AC38 | Accepted UI works at 320/390/768/1024/1440 px, zoom, keyboard and print | P18 | Real browser/a11y/manual print evidence, map alternatives |
| AC39 | Private independent repo, React/single-node cleanup and own release identity | P01–P08 | Inventory/local gate/exact-head/main publication and manifest |
| AC40 | Shared-node release/update/rollback/publication preserves other apps | P19–P21 | Authorized runs/digests, independent checks and scoped cleanup |

## 6. Source sections without a unique test ID

| Source area | Retained implementation obligation | Mapping |
| --- | --- | --- |
| Original §§6/6.1 | Country-only reference-set consent/sensitivity and no location/no route | F07–F08, P10, T24/AC20 |
| Original §§7/32 | Organization/site/product-system distinctions and warehouse/transform boundaries | F03/F11, P14, T14–T17 |
| Original §§8–9/28 | Named required crossing, known mode, via points, deterministic detours/ties and override | F08–F10, P10/P16, T07–T08/T20/T25 |
| Original §§10/29 | Exact source variants, broader taxonomy, expiry, per-unit conversions and proxy consent | F04–F05, P11/P13, T01–T03/T11–T13 |
| Original §§11–12 | Cargo versus gross, volume limits, allocation factor basis and no empty-return doubling | F09, P11/P14, T18–T19/T29 |
| Original §§16–17/31 | Source/formula graph and transparent immutable reports | F13–F14, P11B/P12, V3-18/V3-19 |
| Original §§21/30 | Bounded staged importer plus one reviewed second-provider dataset | F16, P17; add actual importer/selection proof before complete v1 |
| Original §§4/31 | Teaching presentation adapted to owner's About/direct-workspace design | F13/F17, AC01–AC04/AC33; do not restore rejected tutorial dropdowns |
| Original framework/install/auth paths | Next.js/Drizzle/local-no-auth replaced by ASP.NET/React/EF SQLite and approved D02 | Delivery plan §§5/8/12; no Node production server |

## 7. Release evidence rules

### Optional road-beta gate, only if the owner selects it

Use a real `React/CarbonCalculatorRoadBeta` acceptance pair through profile resolution, manifests, CI smoke and deployed-site checks. Do not label a reduced acceptance run `CarbonCalculatorPublicV1` or weaken a full-v1 assertion to pass beta.

| Beta requirement | Required proof before publication |
| --- | --- |
| Approved Dashboard and storage | D02 resolved; P08A complete, stable/partial saves, direct sections and browser-storage truthfulness |
| Source-backed useful calculator | Reviewed timber and brick standard lines, timber production/transport-only/per-unit behavior, source drawers and compatible totals |
| Real road routing | R1–R4, road-only portions of R5–R7 and V3-02–V3-07 with new live inputs; no fixture labelled live |
| Records/documents/reports | P11B/P12/P12A/P12B complete with ownership, import, expiry, safe retrieval and no leaked capabilities |
| Public safety/operations | Actual quotas, CSP, caching/privacy, scoped deployment, exact release identity, update/rollback and isolated runtime restore |
| Honest feature availability | Ferry unavailable, unsupported materials numeric-unavailable, warehouse/importer controls absent until implemented; remaining full-v1 IDs explicitly pending |

All applicable AC criteria must pass; ACs describing a feature not in beta remain pending with its packet and stated availability. Five-material completion, warehouse support, validated ferry inference, second-provider integration and five-beginner evaluation are still mandatory for complete v1. Record the beta's exact remaining rows and resume those packets after publication; publishing beta does not complete the goal.

Complete v1 uses `React/CarbonCalculatorPublicV1` and requires all mandatory source/AC rows, the importer obligation and the complete public/recovery gate. If early beta is not selected, do not add another supported release profile merely for hypothetical future use.

- A green source fixture suite is not production engine proof. A mocked integration is not live provider proof. A browser screenshot is not human beginner feedback.
- Link every passed row to an actual file/run and exact source SHA. If a test changes after its last run, the result is stale until rerun at the required gate.
- Before a public beta, enumerate which rows are required and which complete-v1 rows remain pending. No launch-level decision silently defers a mandatory final-v1 feature.
- Before complete v1, all mandatory source and added product rows have evidence or an explicit owner deferral. Formal compliance certification remains outside scope, not a missing certification blocker.
- Runtime recovery includes SQLite, finalized evidence bytes and snapshot-signing keys. A backup filename or key-presence check alone is insufficient.
