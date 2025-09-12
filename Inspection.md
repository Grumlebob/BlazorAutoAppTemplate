**Inspection Flow Behavior**
- **Trigger**: From `Home` dropdown, select a company to start an inspection.
- **Email Contents**: Sends an Inspection ID (GUID) and a one‑time password via SendGrid.
- **Verification Page**: Navigate to `/inspection/{id}` and enter the password.
- **On Success**: Marks the inspection as verified and sets `CompanyDetails.HasActivatedLatestInspectionEmail = true` for the related company, then redirects to `/inspection/{id}/flow`.
- **On Failure**: Shows an error; user stays on the verification page.

**InspectionFlow Page**
- **Route**: `/inspection/{id}/flow`.
- **Gate**: Calls `GET /api/inspection/{id}/status`; only renders if `Verified = true`.
- **Auto‑Redirect**: If not verified, redirects back to `/inspection/{id}`.
- **Current UI**: Dummy input field “Vessel Name” (no persistence yet).

**Server Slices**
- **StartHullInspectionEmail**: Creates an inspection (ID + salted/hashed password), sends email instructions.
- **VerifyInspectionEmail**: Verifies password, flips company flag to true, exposes status endpoint for gating the flow page.

**Notes**
- **DTO Hygiene**: Client lists companies via DTO without exposing emails; server looks up email for sending.
- **Migrations**: Ensure `Inspections` table includes nullable `VerifiedAtUtc`; `CompanyDetails` includes `HasActivatedLatestInspectionEmail`.
