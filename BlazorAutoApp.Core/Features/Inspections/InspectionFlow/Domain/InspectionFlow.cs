namespace BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Domain;

public class InspectionFlow
{
    public Guid Id { get; set; }
    public string? VesselName { get; set; }
    public InspectionType InspectionType { get; set; }
    public List<InspectionVesselPart> VesselParts { get; set; } = [];
}
