using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;
using InspectionEntity = BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection;
using InspectionFlowEntity = BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow;
using InspectionVesselPartEntity = BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionVesselPart;

namespace BlazorAutoApp.Features.Inspections.InspectionFlow;

public class InspectionFlowServerService(
    IDbContextFactory<AppDbContext> dbFactory,
    ILogger<InspectionFlowServerService> log) : IInspectionFlowApi
{
    private readonly IDbContextFactory<AppDbContext> _dbFactory = dbFactory;
    private readonly ILogger<InspectionFlowServerService> _log = log;

    public async Task<GetInspectionFlowResponse> GetAsync(Guid id, CancellationToken ct = default)
    {
        _log.LogDebug("InspectionFlow Get requested for {InspectionId}", id);

        try
        {
            await using var _db = await _dbFactory.CreateDbContextAsync(ct);
            var flow = await _db.Set<InspectionFlowEntity>()
                .Include(x => x.VesselParts)
                .FirstOrDefaultAsync(x => x.Id == id, ct);
            if (flow is null)
            {
                _log.LogDebug("InspectionFlow {InspectionId} not found; returning default payload", id);
                return new GetInspectionFlowResponse
                {
                    Id = id,
                    VesselName = null,
                    InspectionType = InspectionType.GoProInspection,
                    VesselParts = []
                };
            }

            _log.LogDebug(
                "InspectionFlow {InspectionId} loaded with {PartCount} vessel parts",
                id,
                flow.VesselParts.Count);

            return new GetInspectionFlowResponse
            {
                Id = flow.Id,
                VesselName = flow.VesselName,
                InspectionType = flow.InspectionType,
                VesselParts = [.. flow.VesselParts.Select(vp => new InspectionVesselPartDto
                {
                    Id = vp.Id,
                    PartCode = vp.PartCode
                })]
            };
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "InspectionFlow Get failed for {InspectionId}", id);
            throw;
        }
    }

    public async Task<UpsertInspectionFlowResponse> UpsertAsync(UpsertInspectionFlowRequest req, CancellationToken ct = default)
    {
        _log.LogInformation(
            "InspectionFlow Upsert requested for {InspectionId} with {PartCount} parts",
            req.Id,
            req.VesselParts.Count);

        try
        {
            await using var _db = await _dbFactory.CreateDbContextAsync(ct);
            // Auto-bootstrap inspection if it does not exist yet.
            var insp = await _db.Set<InspectionEntity>()
                .FirstOrDefaultAsync(x => x.Id == req.Id, ct);
            if (insp is null)
            {
                insp = new InspectionEntity
                {
                    Id = req.Id,
                    CreatedAtUtc = DateTime.UtcNow
                };
                _db.Add(insp);
                _log.LogDebug("Inspection {InspectionId} bootstrapped during flow upsert", req.Id);
            }

            var flow = await _db.Set<InspectionFlowEntity>()
                .Include(x => x.VesselParts)
                .FirstOrDefaultAsync(x => x.Id == req.Id, ct);
            if (flow is null)
            {
                flow = new InspectionFlowEntity
                {
                    Id = req.Id
                };
                _db.Add(flow);
                _log.LogDebug("InspectionFlow {InspectionId} created during upsert", req.Id);
            }
            flow.VesselName = req.VesselName;
            flow.InspectionType = req.InspectionType;

            // Sync vessel parts by diffing on PartCode to preserve existing IDs (and linked images)
            var existingByCode = flow.VesselParts.ToDictionary(v => v.PartCode, StringComparer.Ordinal);
            var requestedCodes = new HashSet<string>(req.VesselParts.Select(v => v.PartCode), StringComparer.Ordinal);

            // Remove parts that are no longer requested
            var toRemove = flow.VesselParts.Where(v => !requestedCodes.Contains(v.PartCode)).ToList();
            if (toRemove.Count > 0)
            {
                _db.RemoveRange(toRemove);
            }

            // Add new parts that didn't exist before
            var addedCount = 0;
            foreach (var code in requestedCodes)
            {
                if (!existingByCode.ContainsKey(code))
                {
                    flow.VesselParts.Add(new InspectionVesselPartEntity
                    {
                        PartCode = code,
                        InspectionId = flow.Id
                    });
                    addedCount++;
                }
            }

            await _db.SaveChangesAsync(ct);
            _log.LogDebug(
                "InspectionFlow Upsert applied for {InspectionId}: added {AddedCount}, removed {RemovedCount}",
                req.Id,
                addedCount,
                toRemove.Count);
            return new UpsertInspectionFlowResponse { Success = true };
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "InspectionFlow Upsert failed for {InspectionId}", req.Id);
            throw;
        }
    }
}
