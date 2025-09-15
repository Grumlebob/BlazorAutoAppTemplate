**Inspection Flow Behavior (Passwordless)**
- **Trigger**: From `Home` dropdown, select a company to start an inspection.
- **Email Contents**: Sends only the Inspection ID (GUID) and a direct link to `/inspection/{id}/flow`.
- **First Visit Activation**: On first visit to the Flow page, the server flips `CompanyDetails.HasActivatedLatestInspectionEmail = true` for the related company (idempotent).

**InspectionFlow Page**
- **Route**: `/inspection/{id}/flow`.
- **Gate**: None. Flow loads if the `Inspection` exists. First visit triggers activation via StartHullInspectionEmail slice.
- **Auto-save**: Vessel name, inspection type and the set of selected vessel parts are persisted immediately on change (no Save button).
- **Per-part uploads**: Each selected part row has an Upload button.
  - First clicked upload starts immediately and shows green progress: `Uploading: X / Y`.
  - Additional uploads can be queued by clicking Upload on other parts; their buttons show "Upload image to queue".
  - The queue processes in the order clicked; images appear under their part upon completion.

**Server Slices**
- **StartHullInspectionEmail**: Creates a passwordless `Inspection` (ID + CompanyId), sends email with direct Flow link. Provides `POST /api/start-hull-inspection-email/activate/{id}` to flip the activation flag on first visit.
- **Inspections/HullImages**: All Hull Image endpoints, storage, TUS hooks, and EF config live under `Features/Inspections/HullImages`.

**Notes**
- **DTO Hygiene**: Client lists companies via DTO without exposing emails; server looks up email for sending.
- **Migrations**: `Inspections` table no longer includes password or verified columns; keep `CreatedAtUtc` and FK to `CompanyDetails`. `CompanyDetails.HasActivatedLatestInspectionEmail` is flipped on first Flow visit.
- **Data integrity**: Upserts of `InspectionFlow` still diff by `PartCode` to preserve existing `InspectionVesselPart` Ids so previously uploaded images remain linked.
