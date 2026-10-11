# Portfolio figure production briefs

Parent: [master plan](../../PortfolioStudioImplementation.md). Narrative and section IDs: [PageBriefs.md](PageBriefs.md), [ProjectInventory.md](ProjectInventory.md). Technical defaults: [ExecutionDecisions.md](ExecutionDecisions.md). Each brief belongs to its existing P6 story packet; these are specifications, not created or approved images.

## 1. Shared composition and production contract

Keep the approved Studio shell quiet. Distinctiveness comes from the project's evidence: film credits, run context, coordinated choices, inspection state, maps, system evolution, architectural tradeoffs, spatial results, and administrative boundaries. Do not apply a new themed dashboard or decorative visual system to every page.

- Home cover: 16:10, normally 1280 × 800 master when source resolution permits; one clear subject, no tiny text, title supplied by the card below. Crop only an explicitly approved region. A story cover can reuse the image uncropped; do not repeat it as another figure without a new purpose.
- Figure: native aspect ratio; use a 3:2 or 4:3 canvas for new explanatory diagrams. Screenshots/plots remain uncropped where labels are meaningful. Desktop full reading width, mobile original proportion plus enlargement when necessary. A separate simplified mobile diagram may use the same facts and reading order; no hidden content.
- New diagrams: restrained ink, one accent and semantic labels, numbered stages where order matters, arrows with a named meaning. At most about six main nodes per overview. Put implementation detail in a separate zoomed figure only when useful. Do not make every figure a generic collection of cards.
- Accent suggestions are local figure colors, not new app theme tokens: ImprovedDb amber; GeckoBot green; TraceBack violet; KinoJoin muted rose; Ship Inspections teal; Unlost blue; MiniTwit blue-gray; BestBets indigo; Geospatial research sequential blue; Grumlebob graphite; JobHunt teal. Choose actual shades after contrast review. Include text/shape/line style for meaning; color alone never marks a state or responsibility.
- Screenshots keep source colors in either site theme. Give transparent vectors a predictable opaque plate or reviewed light/dark variant; no CSS inversion. Graphs need visible axes/units/legend and a nearby interpretation. Do not encode missing data as zero.
- New interface recreations are labeled illustrations, never screenshots. Synthetic capture means the actual app running with fictional data; it must not mutate live inboxes, calendars, uploads, forms or bills. Source inspection alone is not runtime verification.
- File names below are logical source stems under `Content/Portfolio/projects/<slug>/media/`. Choose `.svg` for safe local diagrams, `.png` for text-heavy captures, `.jpg` for approved photos. The build makes hashed public variants. No private folder/repository name in a public filename.

### Produce one figure at a time

1. Write its visitor question and select a source revision/report page. Establish permission and the exact claim it supports.
2. Record asset stem, type (actual/synthetic/explanatory/historical), source reference/date, reuse/license, privacy review and caption in the authoring source register. Public attribution is a separate intentional field.
3. Capture with fictional fixtures or select/redraw a permitted artifact. Strip identifying metadata and review the entire visible image, including sidebars, browser chrome, tooltips and filenames.
4. Add caption, alt decision, intrinsic dimensions/crop intent and a prose explanation. Use the suggested wording below only after it matches the actual asset. Keep long diagram explanations in prose, not an enormous alt attribute.
5. Generate variants, preview at 320/390/1440 px in both themes and with 200% text zoom, inspect keyboard enlargement if used, and verify no clipping or unreadable plot labels.
6. Publish through the same story slice as the prose/routes/API/prerender. If evidence is missing, use the listed honest alternative or leave that figure out; never generate a numerical result.

Three purposeful figures can be enough. The lists below are prioritized: make the cover and the primary explanation first, then add supporting evidence that improves the story. No arbitrary minimum asset count delays a good short case study.

## 2. ImprovedDb — P6.1

**Opening:** retain the owner's movie-night motivation. **Visual question:** how does recognizing an actor become a useful browsing journey?

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `cover-browse` / cover, familiar faces | Select a genuine title/cast composition; crop only for the card, preserve full story capture. Remove browser/account details. | Caption names capture date/version. Alt: film or series details alongside its cast, matching the selected capture. |
| `actor-credits` / familiar faces | Real actor credit view with popular/highest-rated/latest grouping where actually present. Number at most three callouts outside the screenshot; do not add invented UI. | Explain how the grouping helps recognition. Alt names the visible ordering/groups rather than enumerating every poster. |
| `score-normalization` / ratings | Explanatory provider-scale → valid-value normalization → combined-score flow. Show missing input as “not included,” and link the deeper rating note. Include actual eligibility rules only when reverified. | “Explanation of the scoring process in the reviewed version.” Alt summarizes normalization and missing-value handling. No fictional numbers portrayed as catalog results. |
| `catalog-publication` / data collection | Source-backed import/validation/catalog/publication boundaries with actual names or neutral responsibilities; mark separate batch/read paths if evidenced. | Cite reviewed revision, distinguish diagram from deployed screenshot. Adjacent prose explains a concrete source-to-page path. |
| `statistics-example` / statistics | One real graph with complete axis/legend and source period. Choose a question understandable without knowing the tool. | Name the question, actual units and dataset period; interpret only the shown result. |
| `historical-models` / machine learning | Genuine historical-model view plus a compact text explanation of retrospective signals and limitations. | Avoid probabilities/accuracy claims not established by evidence. Preserve date/model version where known. |

Fallback: omit unverified graph/model counts and conflicting cutoff claims; the real browsing story and an honestly sourced scoring explanation still work. Do not recreate posters without reviewing reuse rights.

## 3. GeckoBot — P6.9

**Opening suggestion:** “Booking messages, organized.” **Visual question:** what happens to one booking message and where does Outlook enter the workflow?

Use fictional booking `DEMO-104`, sender `visitor@example.test` and staff `Alex Example`. Use no real customer/staff data and no executable mailbox integration during illustration work.

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `booking-overview` / cover, workflow | Explanatory triptych: example message → parsed booking fields → calendar action. A small “Illustrative example” label stays visible. | “A fictional example of the documented booking workflow.” Alt summarizes the three stages. |
| `booking-branches` / workflow | Read source branches first; diagram supported new/change/cancel paths, each with its actual outcome. Mark unverified sending/review behavior as omitted, not an invented approval gate. | Identify source-backed branching; prose covers parser/Outlook boundary. |
| `controls-example` / control and review | Prefer a safely isolated actual Tkinter capture with fictional values. If not possible, use a labeled explanatory control inventory, not fake UI. | Name actual controls only. Alt identifies the visible settings/actions. |
| `integration-boundary` / implementation | Tkinter/settings → parser → Outlook COM boundary, arrows labeled configuration/parsed fields/calendar operation as supported. | “Responsibilities in the reviewed source; runtime use was not reproduced.” Revise that statement only after real evidence. |

Keep the private repository URL out of public buttons. Deleted MailDemo is not an active source or a reason to publish timezone claims from different code.

## 4. TraceBack — P6.3

**Opening suggestion:** “Keep the context of a run.” **Visual question:** what is preserved, what is referenced, and what must still exist later?

Use a fictional project `River study`, input `measurements.csv`, processing box `clean.py` and output `summary.csv`; show these only as conceptual labels unless captured in the real prototype.

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `pipeline-example` / cover, pipeline | Input → processing box → output, with a small enclosing project/pipeline label. Prefer synthetic real UI; otherwise a labeled explanation. | The caption establishes prototype/example status. Alt names the pipeline and its three stages. |
| `run-record` / saved evidence | A short sanitized genuine manifest excerpt next to a diagram of metadata versus payload. Highlight only evidenced fields, not invented schema keys. | Explain what the record identifies; never imply it executes the pipeline. |
| `reference-snapshot` / reproducibility | Two aligned columns: reference to a source location, stored snapshot of selected content. Add a separate environment boundary below, listing only documented responsibilities. | “A saved reference and a saved snapshot preserve different things.” Adjacent prose addresses mutable inputs and environment limits. |
| `revisit-history` / revisiting | Synthetic actual history/recreate selections capture with one example run. | Explain restoration of selections/context; no guarantee of identical scientific results. |

Do not use real institution paths, tokens or remote connection details. If capture is unavailable, the source-backed boundary comparison supplies a useful primary figure.

## 5. KinoJoin — P6.2

**Opening suggestion:** “A cinema plan everyone can weigh in on.” **Visual question:** how do separate preferences become a choice the host can confirm?

Use a fictional event `Friday cinema`, host `Alex`, participants `Sam` and `Robin`, and explicitly fictional showtimes. Keep the same labels across all figures.

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `event-cover` / cover | Safely captured event-creation screen: event name, candidate showtimes and deadline if supported. | “Actual interface with fictional event details.” Alt describes creating an event with candidate showtimes. |
| `choice-journey` / shared event, preferences | Four-stage explanation: narrow showtimes → share event → collect preferences → host confirms. Match actual code; external booking/calendar remains a distinct handoff. | Explicitly distinguish participant input from host decision. No automatic consensus claim. |
| `preferences-result` / preferences | Actual fictional preference/result screen at legible scale. If figures are illustrative, show discrete example selections, not a claim about the scoring algorithm. | State what the visible selections/result show, without inferring unseen calculations. |
| `calendar-boundary` / plan, data model | Event/participant/showtime relationships plus the documented calendar/booking boundary. Split into two figures if labels become dense. | Source revision and supported export behavior; no verified compatibility claim for every calendar client. |

Avoid payment/ticket-purchase imagery. If safe local capture cannot run, publish a labeled workflow and domain diagram without claiming screenshots exist.

## 6. Ship Inspections — P6.5

**Opening suggestion:** “An observation belongs to a part.” **Visual question:** how does a part selection remain connected to its notes and image upload?

Use fictional vessel `Demo Vessel`, part `Port bow panel` and permitted example imagery. Never submit to a live inspection service.

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `vessel-context` / cover, navigating | Actual segmented-vessel view with one selected area and a matching part label. | Identify prototype/synthetic capture; alt describes selected area and its context. |
| `observation-detail` / observations | Selected part → actual condition/note fields → attached images. Keep source terminology; no invented condition score. | Explain attachment to the selected part; photograph attribution where required. |
| `upload-offset` / reliable uploads | Source-verified request sequence showing create, PATCH chunk, interrupted transfer, HEAD offset and resumed PATCH only where implemented. Use sequence numbering; offsets are explicitly schematic or actual capture values. | “Protocol explanation for the reviewed upload path.” Never infer browser-reload recovery from session resume. |
| `image-ready` / usable images | Actual upload state/thumbnail capture or a sourced validation → metadata → thumbnail/original flow. | Separate upload completion from any later processing or unsupported AI analysis. |

Resolve code/docs upload limits before including numbers. Permitted illustrations can replace sensitive photos; a visible AI field is not model evidence.

## 7. Unlost — P6.4

**Opening suggestion:** “Finding a route through the map.” **Visual question:** how do the map, address lookup and pathfinding fit together?

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `map-overview` / cover, map data | Genuine report map view with source attribution, historical date/context and unchanged geography. Crop card preview only; retain full map in story. | Historical application view, not a newly running site. Alt describes the map extent and visible route/interface. |
| `address-route` / search, routes | Genuine address/search and route artifact, using reviewed report examples. Remove personal locations if present. | Explain the supported search and routing controls, including travel modes only when evidenced. |
| `search-comparison` / Dijkstra/A* | Existing explored-node/path figure, or faithful attributed redraw from the report. Align endpoints and legend; distinguish explored nodes from selected path. | Explain the search difference. Do not infer new measured speedup or optimality. |
| `spatial-index` / spatial data | Source-backed Kd-tree/spatial index explanation with tiny schematic points labeled “illustration.” | Explain the operation the index supports; no invented benchmark. |

Use available artifacts; recovering Java code or inspecting another team's archive is not required. Review team attribution and map/figure reuse.

## 8. MiniTwit — P6.6

**Opening suggestion:** “A small application, a changing system.” **Visual question:** what changed in the application and how did the team learn to deliver and observe it?

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `timeline-view` / cover | Genuine historical microblog view, with permitted or fictional account content. | Historical team/course application; do not imply the old deployment is live. |
| `system-evolution` / evolution | Two sourced architectures with only reviewed changes: earlier Flask boundary and later client/.NET API/storage boundary. Add actual dates only when evidenced. | Explain the change and responsibility split; no invented intermediate phases. |
| `delivery-path` / delivery | Source checks → image build → actual deployment mechanism → verified running app. Include only the inspected historical workflow, not Portfolio's pipeline. | “Delivery workflow at the recorded project revision.” |
| `operational-question` / observability | One genuine Seq/metric figure with a visible time range and a plain question above, such as response failures only if that metric exists. | Define the metric/window and interpret the shown evidence; don't extract uptime/throughput from an unrelated graph. |

A clean sourced architecture diagram is preferable to a sensitive raw log screenshot. Omit unavailable operational results rather than fabricating a dashboard.

## 9. BestBets — P6.7

**Opening suggestion:** “Architectural choices under uneven demand.” **Visual question:** how did performance, modifiability and safety influence the final design?

Preferred Exam/deck text review now supports the specifics below; selected visual pages/slides still need inspection before extraction/redrawing. Keep spring 2025 team/design/prototype context. Restrict this page to academic architectural reasoning; no live financial/betting interface is implemented in Portfolio.

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `design-overview` / cover, views | Simplify the final responsibilities: Sports Odds Updater → Trigger Order Broker → subscribed trigger orders; separate request path through load balancing, kernel/plugin and per-transaction actors. Use Exam figures 20–23 and final evaluation. | Label design study; explain that UI odds updates were still undecided. Do not reproduce the retired global broker as the final UI-update path. |
| `quality-scenario` / requirements | A compact stimulus/environment/response/measure figure from Exam p.17: user count grows 1,000 → 100,000 in 10 minutes; page response target 2 seconds for 95% of requests; odds-update target 3 seconds. | All numbers labeled “Design targets,” not measured capacity. Keep the target's distinct measures intact. |
| `prototype-comparison` / evaluation | Two columns, actor model and load balancer, matching deck slides 14–17: hypotheses, reported qualitative observation, limitations. No numerical bar chart without actual measured series/units. | Explicit threats: retries not correctly simulated, identical simulated provider logic, local/real network differences. |
| `combined-design` / tradeoffs | Actor-only and load-balancer-only alternatives converge on load-balanced actor model; annotate performance motivation, transaction separation, added hop/complexity. Use final Exam p.62 and deck slide 18. | Distinguish deck's proposed combination from report's later selected design. aSQA scores, if used, are team evaluations on a 1–5 scale, not performance measurements. |

Do not carry identifying presentation fixture/infrastructure references into public diagrams. The report's separate Zeguu reconstruction appendix is not part of BestBets and creates no new portfolio entry. Unknown DB topology/UI update transport stays explicitly unresolved in the historical project story; Portfolio planning must not pretend to solve that project's architecture retroactively.

## 10. Geospatial research — P6.8

**Opening suggestion:** “Spatial patterns, carefully interpreted.” **Visual question:** what do the selected maps show and which assumptions limit that interpretation?

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `study-area` / cover, research question | Genuine study-area map with title/period and attribution. Avoid a decorative crime heatmap without a denominator. | Describe area/data period; no current safety or causal statement. |
| `data-alignment` / data | Crime records + OSM amenities + geographic boundaries → documented cleaning/matching → analyzed units. Name actual spatial join/unit after report review. | Explain mismatched dates, missing values or boundary issues only when supported. |
| `mapped-result` / patterns | One genuine choropleth or point-pattern output, retaining legend, units, normalization and missing-data encoding. | Adjacent prose states one shown pattern and its limit. Raw counts are not rates. |
| `analysis-result` / methods/findings | An actual selected spatial-method plot paired with method question, result and limitation. Preserve axes/sample/uncertainty where present. | Label historical analysis. No new result or notebook execution for decoration. |

Reject illegible graph exports rather than silently redrawing unknown values. For tiny figures, obtain the original or faithfully reproduce from available source data as a separately recorded task.

## 11. Grumlebob — P6.10

**Opening proposal:** “Tools for recurring tasks.” **Visual question:** which approved recurring tasks are connected and where does review happen?

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `tools-overview` / cover, introduction | Generic AHK/Python tools illustration with no specific excluded domain, real accounts or identifiable source artifact. Label as explanatory. | Public copy must match the owner's approved explanation. No implied company/client/impact. |
| `task-boundary` / automation | Approved input → transformation → output plus actual review/control boundary only if the explanation supports it. Separate independent tools instead of inventing one integrated system. | Describe technical responsibilities, not the restricted originating workflow. |
| `fictional-records` / bookkeeping/billing | Only if specifically supported: fictional rows `Example item A/B` and an illustrative totals/check handoff. No real invoice, provider, payment action or transaction result. | Mark fictional. Alt explains the generic record organization. Never infer automated payment collection. |

Prepare a short proposed description and source-free diagram for the owner to approve when this packet is reached. Without that input the story remains draft; other packets continue. Publication review includes text, image metadata, URLs, alt/caption, source maps, filename and social preview.

## 12. JobHunt — P6.11

**Opening recommendation:** “Administrative help. Personal decisions.” **Visual question:** which steps are assisted, and which decisions remain with the applicant?

| Asset / placement | Composition and labels | Caption / alt direction |
| --- | --- | --- |
| `application-overview` / cover | Quiet illustrative posting/document/tracker arrangement with fictional `Example role`, organization `Example Company`, no personal documents. | “Illustrative administrative workflow.” No employer-receipt claim. |
| `responsibility-flow` / eight-step flow | Use all eight PageBriefs stages. Desktop two rows of four with explicit 1–8 reading order; mobile a vertical ordered list. Stages 1/8 Personal; stage 5 “Personal authorship; drafting assistance may be used” where current docs support it; other verified admin steps Assisted. | Include the complete textual equivalent. Omit account-creation claims; portal preparation does not imply autonomous registration. |
| `information-handoff` / organization/preparation | Fictional posting details → selected document references → reviewed form/attachment handoff. Distinguish local prepared state from external submission. | “Prepared” is not “received.” No interactive form or real submission during media work. |
| `duplicate-state` / reliability | Diagram only actual reviewed duplicate/state checks; unsupported safeguards become a clearly identified lesson/intention in prose. | Separate implemented controls, intended boundaries and limitations. |

Adapt the existing workflow concept, preserving shared Studio styling. No carousel, autoplay, hidden mandatory steps or new app-specific widget engine. The personal/manual-writing principle is an intention; do not present it as an enforced current implementation when assisted drafting exists.

## 13. Finish a page without inventing facts

At the visual checkpoint, record its opening, chosen figure stems, source revision/permission, final captions/alts, missing evidence and how it was handled. Ask whether a visitor can explain the project's purpose, one design decision and its limitations from prose plus figures. Remove redundant captures, decorative charts and unsupported outcome claims. Apply the PageBriefs publication checklist and update the existing P6 row, not a separate image-only completion ledger.
