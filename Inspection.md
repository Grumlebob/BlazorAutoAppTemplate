**Inspection Flow Behavior**
- **Trigger**: From `Home`, click `Start New Inspection` to generate a new inspection id and open `/inspection/{id}/flow`.
- **No authentication**: The flow is fully direct and does not depend on external verification or separate start steps.

**InspectionFlow Page**
- **Route**: `/inspection/{id}/flow`.
- **Image-first selection**: Vessel parts are selected from clickable ship image segments (`ImageSegmentToggle`).
- **Viewing angle buttons**: `Starboard`, `Port`, `Flat Bottom`, `Rudder`, `Propeller`, `Other`.
- **Starboard/port horizontal divider**: Side views include a thin non-interactive divider line.
- **Single active-part card**: Clicking a segment activates that vessel part and shows one card with part details form + uploads.
- **Auto-save**: Vessel name, inspection type, and selected vessel parts save immediately.
- **Part status states**:
  - `Incomplete` (no saved details)
  - `Partially Completed` (saved details, no uploaded image)
  - `Fully Completed` (saved details + image uploaded)
  - `Inspection Not Needed` (marked explicitly in the form flow)
- **Status badges**: Top badges show counts for the four statuses and hotspot colors follow the same state.

**Server Slices**
- **Inspections/InspectionFlow**:
  - Upsert auto-bootstraps a missing `Inspection` row.
  - Upsert diffs vessel parts by `PartCode` to preserve existing `InspectionVesselPart` ids.
- **Inspections/HullImages**:
  - All image endpoints, storage, thumbnailing, TUS upload handling, and part-linking.
- **Inspections/VesselPartDetails**:
  - Per-part details persistence used for completion-state logic.

**Data Integrity**
- **Id stability**: Vessel parts retain ids when still present, so linked images/details remain attached.
- **Auto-pruning mismatch parts**: Persisted parts outside the current image mapping are pruned on load/save to keep UI and data aligned.
