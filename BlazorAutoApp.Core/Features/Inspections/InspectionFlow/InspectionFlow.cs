using BlazorAutoApp.Core.Features.HullImages;

namespace BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

public enum InspectionType
{
    GoProInspection = 0,
    DivingInspection = 1,
    ROVInspection = 2,
    HullCleaning = 3,
    PropellerCleaning = 4
}

public class InspectionFlow
{
    public Guid Id { get; set; } // same as VerifyInspectionEmail.Inspection.Id
    public int CompanyId { get; set; }
    public string? VesselName { get; set; }
    public InspectionType InspectionType { get; set; }
    public List<InspectionVesselPart> VesselParts { get; set; } = new();
}

public class InspectionVesselPart
{
    public int Id { get; set; }
    public Guid InspectionId { get; set; }
    public required string PartCode { get; set; }
    public ICollection<HullImage> HullImages { get; set; } = new List<HullImage>();
}

// DTOs
public class GetInspectionFlowResponse
{
    public Guid Id { get; set; }
    public int CompanyId { get; set; }
    public string? VesselName { get; set; }
    public InspectionType InspectionType { get; set; }
    public List<InspectionVesselPartDto> VesselParts { get; set; } = new();
}

public class InspectionVesselPartDto
{
    public int? Id { get; set; }
    public required string PartCode { get; set; }
}

public class UpsertInspectionFlowRequest
{
    public required Guid Id { get; set; }
    public string? VesselName { get; set; }
    public InspectionType InspectionType { get; set; }
    public List<InspectionVesselPartDto> VesselParts { get; set; } = new();
}

public class UpsertInspectionFlowResponse
{
    public bool Success { get; set; }
    public string? Error { get; set; }
}

public interface IInspectionFlowApi
{
    Task<GetInspectionFlowResponse> GetAsync(Guid id, CancellationToken ct = default);
    Task<UpsertInspectionFlowResponse> UpsertAsync(UpsertInspectionFlowRequest req, CancellationToken ct = default);
    Task<GetVesselsResponse> GetVesselsAsync(CancellationToken ct = default);
}

public class Vessel
{
    public int Id { get; set; }
    public required string Name { get; set; }
}

public class GetVesselsResponse
{
    public List<VesselDto> Items { get; set; } = new();
}

public class VesselDto
{
    public int Id { get; set; }
    public required string Name { get; set; }
}
