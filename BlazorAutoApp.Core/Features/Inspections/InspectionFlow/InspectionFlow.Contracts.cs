namespace BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

public class GetInspectionFlowResponse
{
    public Guid Id { get; set; }
    public string? VesselName { get; set; }
    public InspectionType InspectionType { get; set; }
    public List<InspectionVesselPartDto> VesselParts { get; set; } = [];
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
    public List<InspectionVesselPartDto> VesselParts { get; set; } = [];
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

public class GetVesselsResponse
{
    public List<VesselDto> Items { get; set; } = [];
}

public class VesselDto
{
    public int Id { get; set; }
    public required string Name { get; set; }
}
