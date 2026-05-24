using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Contracts;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Domain;

namespace BlazorAutoApp.Core.Features.Inspections.InspectionFlow.UseCases.UpsertInspectionFlow;

public class UpsertInspectionFlowRequest
{
    public required Guid Id { get; set; }
    public string? VesselName { get; set; }
    public InspectionType InspectionType { get; set; }
    public List<InspectionVesselPartDto> VesselParts { get; set; } = [];
}
