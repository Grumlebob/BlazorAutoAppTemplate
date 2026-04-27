**Inspection Flow Behavior (Passwordless)**
- **Trigger**: From `Home` dropdown, select a company to start an inspection.
- **Email Contents**: Sends only the Inspection ID (GUID) and a direct link to `/inspection/{id}/flow`.
- **First Visit Activation**: On first visit to the Flow page, the server flips `CompanyDetails.HasActivatedLatestInspectionEmail = true` for the related company (idempotent).

**InspectionFlow Page**
- **Route**: `/inspection/{id}/flow`.
- **Gate**: None. Flow loads if the `Inspection` exists. First visit triggers activation via StartHullInspectionEmail slice.
- **Image-first selection**: Vessel parts are selected only from the existing clickable image segments (`ImageSegmentToggle`). The checkbox list is removed.
- **Viewing angle buttons**: A button group above the ship switches between `Starboard`, `Port`, `Flat Bottom`, `Rudder`, `Propeller`, and `Other` views.
- **Starboard/port horizontal divider**: Side views include a thin non-interactive horizontal divider line; it is not a vessel part.
- **Active part workflow**: Clicking a segment activates that mapped vessel part and opens a single `VesselPartForm` panel for the active part.
- **Auto-save**: Vessel name, inspection type and selected vessel parts are persisted immediately on change (no Save button).
- **Part status states**: Hotspots visualize `Not selected`, `Selected`, `Active`, and `Completed` states.
- **Per-part uploads**: The active part form has upload support; uploaded files are linked to the active `InspectionVesselPart`.

**Server Slices**
- **StartHullInspectionEmail**: Creates a passwordless `Inspection` (ID + CompanyId), sends email with direct Flow link. Provides `POST /api/start-hull-inspection-email/activate/{id}` to flip the activation flag on first visit.
- **Inspections/HullImages**: All Hull Image endpoints, storage, TUS hooks, and EF config live under `Features/Inspections/HullImages`.

**Notes**
- **DTO Hygiene**: Client lists companies via DTO without exposing emails; server looks up email for sending.
- **Migrations**: `Inspections` table no longer includes password or verified columns; keep `CreatedAtUtc` and FK to `CompanyDetails`. `CompanyDetails.HasActivatedLatestInspectionEmail` is flipped on first Flow visit.
- **Data integrity**: Upserts of `InspectionFlow` diff by `PartCode` to preserve existing `InspectionVesselPart` Ids so previously uploaded images and details remain linked.
- **Auto-pruning mismatch parts**: Any persisted vessel parts that do not match the image-mapped segment set are removed on load/save to keep flow data aligned with selectable image segments.
