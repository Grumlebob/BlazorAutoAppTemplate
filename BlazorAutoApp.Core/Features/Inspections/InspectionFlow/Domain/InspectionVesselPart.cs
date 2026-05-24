using BlazorAutoApp.Core.Features.Inspections.HullImages.Domain;

namespace BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Domain;

public class InspectionVesselPart
{
    public int Id { get; set; }
    public Guid InspectionId { get; set; }
    public required string PartCode { get; set; }
    public ICollection<HullImage> HullImages { get; set; } = [];
}
