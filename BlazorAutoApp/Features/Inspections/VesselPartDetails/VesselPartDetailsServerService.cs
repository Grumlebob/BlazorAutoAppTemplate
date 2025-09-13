using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails;

namespace BlazorAutoApp.Features.Inspections.VesselPartDetails;

public class VesselPartDetailsServerService(AppDbContext db, ILogger<VesselPartDetailsServerService> log) : IVesselPartDetailsApi
{
    private readonly AppDbContext _db = db;
    private readonly ILogger<VesselPartDetailsServerService> _log = log;

    public async Task<GetVesselPartDetailsResponse> GetAsync(int vesselPartId, CancellationToken ct = default)
    {
        BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.VesselPartDetails? details = null;
        try
        {
            // Load details; if missing, return empty template
            details = await _db.Set<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.VesselPartDetails>()
                .Include(d => d.Fouling)
                .Include(d => d.Coating)
                .Include(d => d.Hull)
                .Include(d => d.Rating)
                .FirstOrDefaultAsync(d => d.InspectionVesselPartId == vesselPartId, ct);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "VesselPartDetails GetAsync likely before migrations; returning template");
        }

        if (details is null)
        {
            return new GetVesselPartDetailsResponse
            {
                InspectionVesselPartId = vesselPartId,
                Fouling = Enum.GetValues<FoulingType>().Select(t => new FoulingObservationDto
                {
                    FoulingType = t,
                    IsPresent = false,
                    CoveragePercent = null
                }).ToList(),
                Coating = new CoatingConditionDto(),
                Hull = new HullConditionDto(),
                Rating = new HullRatingDto { Rating = HullRatingValue.Clean }
            };
        }

        return new GetVesselPartDetailsResponse
        {
            InspectionVesselPartId = vesselPartId,
            Fouling = details.Fouling
                .OrderBy(f => f.FoulingType)
                .Select(f => new FoulingObservationDto
                {
                    FoulingType = f.FoulingType,
                    IsPresent = f.IsPresent,
                    CoveragePercent = f.CoveragePercent
                }).ToList(),
            Coating = details.Coating is null ? new CoatingConditionDto() : new CoatingConditionDto
            {
                IntactPercent = details.Coating.IntactPercent,
                Peeling = details.Coating.Peeling,
                Blisters = details.Coating.Blisters,
                Scratching = details.Coating.Scratching
            },
            Hull = details.Hull is null ? new HullConditionDto() : new HullConditionDto
            {
                IntegrityPercent = details.Hull.IntegrityPercent,
                Corrosion = details.Hull.Corrosion,
                Dents = details.Hull.Dents,
                Cracks = details.Hull.Cracks
            },
            Rating = details.Rating is null ? new HullRatingDto { Rating = HullRatingValue.Clean } : new HullRatingDto
            {
                Rating = details.Rating.Rating,
                Rationale = details.Rating.Rationale
            }
        };
    }

    public async Task<UpsertVesselPartDetailsResponse> UpsertAsync(UpsertVesselPartDetailsRequest req, CancellationToken ct = default)
    {
        // Ensure vessel part exists
        var vpExists = await _db.InspectionVesselParts.AsNoTracking().AnyAsync(x => x.Id == req.InspectionVesselPartId, ct);
        if (!vpExists)
        {
            return new UpsertVesselPartDetailsResponse { Success = false, Error = "Vessel part not found" };
        }

        BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.VesselPartDetails? details = null;
        try
        {
            details = await _db.Set<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.VesselPartDetails>()
                .Include(d => d.Fouling)
                .Include(d => d.Coating)
                .Include(d => d.Hull)
                .Include(d => d.Rating)
                .FirstOrDefaultAsync(d => d.InspectionVesselPartId == req.InspectionVesselPartId, ct);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "VesselPartDetails UpsertAsync failed (likely migrations missing)");
            return new UpsertVesselPartDetailsResponse { Success = false, Error = "Database not migrated for vessel part details." };
        }

        if (details is null)
        {
            details = new BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.VesselPartDetails
            {
                InspectionVesselPartId = req.InspectionVesselPartId
            };
            _db.Add(details);
        }

        // Upsert singletons
        details.Coating ??= new CoatingCondition { VesselPartDetailsId = details.Id };
        details.Coating.IntactPercent = Clamp(req.Coating.IntactPercent);
        details.Coating.Peeling = req.Coating.Peeling;
        details.Coating.Blisters = req.Coating.Blisters;
        details.Coating.Scratching = req.Coating.Scratching;

        details.Hull ??= new HullCondition { VesselPartDetailsId = details.Id };
        details.Hull.IntegrityPercent = Clamp(req.Hull.IntegrityPercent);
        details.Hull.Corrosion = req.Hull.Corrosion;
        details.Hull.Dents = req.Hull.Dents;
        details.Hull.Cracks = req.Hull.Cracks;

        details.Rating ??= new HullRating { VesselPartDetailsId = details.Id };
        details.Rating.Rating = req.Rating.Rating;
        details.Rating.Rationale = req.Rating.Rationale;

        // Sync fouling entries
        var byType = details.Fouling.ToDictionary(f => f.FoulingType);
        foreach (var dto in req.Fouling)
        {
            if (!byType.TryGetValue(dto.FoulingType, out var f))
            {
                f = new FoulingObservation { VesselPartDetailsId = details.Id, FoulingType = dto.FoulingType };
                details.Fouling.Add(f);
            }
            f.IsPresent = dto.IsPresent;
            f.CoveragePercent = dto.IsPresent ? ClampNullable(dto.CoveragePercent) : null;
        }

        await _db.SaveChangesAsync(ct);
        return new UpsertVesselPartDetailsResponse { Success = true };
    }

    private static int Clamp(int v) => Math.Max(0, Math.Min(100, v));
    private static int? ClampNullable(int? v) => v.HasValue ? Clamp(v.Value) : null;
}
