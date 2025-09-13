## Vessel Part Details — Implementation Plan

This plan adds per‑vessel‑part forms to the Inspection Flow, following the project’s vertical slice pattern under `Features/*`. You will run the EF migrations; I’ll wire everything end‑to‑end so the UI and APIs compile and are ready.

Goals:
- Each selected part in the Flow page renders its own form component capturing four categories:
  - Fouling Condition: checkboxes for Slime, Algae, Grass, Barnacles, Mussels, Tubeworms. When checked, show integer Coverage (%) 0–100.
  - Coating Condition: Intact Coating (%) 0–100 + flags Peeling, Blisters, Scratching.
  - Hull Condition: Hull integrity (%) 0–100 + flags Corrosion, Dents, Cracks.
  - Hull Rating: radio 0–4 with the provided scale.
- Persist per‑part details in DB; read/write via vertical slice API.
- Reuse existing image upload linked to `InspectionVesselPart.Id`.

Architecture:
- Core (DTOs + Entities): `BlazorAutoApp.Core/Features/Inspections/VesselPartDetails/*`
- Server slice: `BlazorAutoApp/Features/Inspections/VesselPartDetails/*` (endpoints, EF config, server service)
- Client service: `BlazorAutoApp.Client/Services/VesselPartDetailsClientService.cs`
- Blazor UI: `BlazorAutoApp.Client/Pages/Inspection/Components/VesselPartForm.razor` used by `Pages/Inspection/Flow.razor` for each selected part.

Domain model (Core):
- Enums: `FoulingType { Slime, Algae, Grass, Barnacles, Mussels, Tubeworms }`, `HullRatingValue { Clean=0, Light=1, Medium=2, Heavy=3, VeryHeavy=4 }`.
- Entities (owned by `InspectionVesselPart`):
  - `VesselPartDetails` (1:1) — FK to `InspectionVesselPart.Id`.
  - `FoulingObservation` (1:n) — FoulingType, IsPresent, CoveragePercent (0–100 or null when not present).
  - `CoatingCondition` (1:1) — IntactPercent (0–100), Peeling, Blisters, Scratching.
  - `HullCondition` (1:1) — IntegrityPercent (0–100), Corrosion, Dents, Cracks.
  - `HullRating` (1:1) — Rating (0–4), Rationale (optional).

Database (you run migrations):
- Tables: `VesselPartDetails`, `FoulingObservations`, `CoatingConditions`, `HullConditions`, `HullRatings` keyed by `InspectionVesselPartId`.
- Constraints: Range checks 0–100; `CoveragePercent` required when `IsPresent=true`.
- Index: unique 1:1 on `InspectionVesselPartId` for the three singletons.

API surface:
- `GET /api/vessel-part-details/{vesselPartId:int}` → full detail payload.
- `PUT /api/vessel-part-details/{vesselPartId:int}` → upsert full payload.

Blazor Flow wiring:
- In `Flow.razor`, for each selected part that has an `Id`, render `<VesselPartForm VesselPartId="@vp.Id.Value" />` under a “Part Details” section.
- The component loads via client service, handles validation, and saves on demand.

Validation:
- Percentages `[0,100]`.
- If checkbox checked ⇒ require Coverage (%) and keep in range.

Sequence to complete:
1) Add Core DTOs/entities/enums and API interface.
2) Add server service + endpoints + EF configurations (no migrations run yet).
3) Add client service.
4) Add `VesselPartForm.razor` and wire into `Flow.razor`.
5) You run migrations; I’ll confirm once done.

Next step after you migrate:
- Verify GET/PUT roundtrip for a part; confirm charts can later use these fields (optional).

