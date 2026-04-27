using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

namespace BlazorAutoApp.Features.Inspections.InspectionFlow;

public class InspectionFlowServerService(IDbContextFactory<AppDbContext> dbFactory, ILogger<InspectionFlowServerService> log) : IInspectionFlowApi
{
    private readonly IDbContextFactory<AppDbContext> _dbFactory = dbFactory;
    private readonly ILogger<InspectionFlowServerService> _log = log;

    public async Task<GetInspectionFlowResponse> GetAsync(Guid id, CancellationToken ct = default)
    {
        await using var _db = await _dbFactory.CreateDbContextAsync(ct);
        var flow = await _db.Set<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow>()
            .Include(x => x.VesselParts)
            .FirstOrDefaultAsync(x => x.Id == id, ct);
        if (flow is null)
        {
            return new GetInspectionFlowResponse
            {
                Id = id,
                VesselName = null,
                InspectionType = InspectionType.GoProInspection,
                VesselParts = new()
            };
        }
        return new GetInspectionFlowResponse
        {
            Id = flow.Id,
            VesselName = flow.VesselName,
            InspectionType = flow.InspectionType,
            VesselParts = flow.VesselParts.Select(vp => new InspectionVesselPartDto
            {
                Id = vp.Id,
                PartCode = vp.PartCode
            }).ToList()
        };
    }

    public async Task<UpsertInspectionFlowResponse> UpsertAsync(UpsertInspectionFlowRequest req, CancellationToken ct = default)
    {
        await using var _db = await _dbFactory.CreateDbContextAsync(ct);
        // Auto-bootstrap inspection if it does not exist yet.
        var insp = await _db.Set<BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection>()
            .FirstOrDefaultAsync(x => x.Id == req.Id, ct);
        if (insp is null)
        {
            insp = new BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection
            {
                Id = req.Id,
                CreatedAtUtc = DateTime.UtcNow
            };
            _db.Add(insp);
        }

        var flow = await _db.Set<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow>()
            .Include(x => x.VesselParts)
            .FirstOrDefaultAsync(x => x.Id == req.Id, ct);
        if (flow is null)
        {
            flow = new BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow
            {
                Id = req.Id
            };
            _db.Add(flow);
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
        foreach (var code in requestedCodes)
        {
            if (!existingByCode.ContainsKey(code))
            {
                flow.VesselParts.Add(new BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionVesselPart
                {
                    PartCode = code,
                    InspectionId = flow.Id
                });
            }
        }

        await _db.SaveChangesAsync(ct);
        return new UpsertInspectionFlowResponse { Success = true };
    }

    public async Task<GetVesselsResponse> GetVesselsAsync(CancellationToken ct = default)
    {
        await using var _db = await _dbFactory.CreateDbContextAsync(ct);
        var items = await _db.Vessels.AsNoTracking().OrderBy(v => v.Name)
            .Select(v => new VesselDto { Id = v.Id, Name = v.Name }).ToListAsync(ct);
        return new GetVesselsResponse { Items = items };
    }
}
