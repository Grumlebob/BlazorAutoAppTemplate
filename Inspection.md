**Inspection Flow Behavior**
- **Trigger**: From `Home` dropdown, select a company to start an inspection.
- **Email Contents**: Sends an Inspection ID (GUID) and a one‑time password via SendGrid.
- **Verification Page**: Navigate to `/inspection/{id}` and enter the password.
- **On Success**: Marks the inspection as verified and sets `CompanyDetails.HasActivatedLatestInspectionEmail = true` for the related company, then redirects to `/inspection/{id}/flow`.
- **On Failure**: Shows an error; user stays on the verification page.

**InspectionFlow Page**
- **Route**: `/inspection/{id}/flow`.
- **Gate**: Calls `GET /api/inspection/{id}/status` via `IVerifyInspectionEmailApi`; only renders if `Verified = true`.
- **Auto-Redirect**: If not verified, redirects back to `/inspection/{id}`.
- **Auto-save**: Vessel name, inspection type and the set of selected vessel parts are persisted immediately on change (no Save button).
- **Per-part uploads**: Each selected part row has an Upload button.
  - First clicked upload starts immediately and shows green progress: `Uploading: X / Y`.
  - Additional uploads can be queued by clicking Upload on other parts; their buttons show "Upload image to queue".
  - The queue processes in the order clicked; images appear under their part upon completion.

**Server Slices**
- **StartHullInspectionEmail**: Creates an inspection (ID + salted/hashed password), sends email instructions.
- **VerifyInspectionEmail**: Verifies password, flips company flag to true, exposes status endpoint for gating the flow page. Interface renamed to `IVerifyInspectionEmailApi`.
- **Inspections/HullImages**: All Hull Image endpoints, storage, TUS hooks, and EF config live under `Features/Inspections/HullImages`.

**Notes**
- **DTO Hygiene**: Client lists companies via DTO without exposing emails; server looks up email for sending.
- **Migrations**: Ensure `Inspections` table includes nullable `VerifiedAtUtc`; `CompanyDetails` includes `HasActivatedLatestInspectionEmail`.
- **Data integrity**: Upserts of `InspectionFlow` now diff by `PartCode` to preserve existing `InspectionVesselPart` Ids so previously uploaded images remain linked.
