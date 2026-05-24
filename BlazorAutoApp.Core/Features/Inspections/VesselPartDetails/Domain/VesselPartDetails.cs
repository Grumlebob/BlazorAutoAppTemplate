namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;

public class VesselPartDetails
{
    public int Id { get; set; }
    public required int InspectionVesselPartId { get; set; }

    public CoatingCondition? Coating { get; set; }
    public HullCondition? Hull { get; set; }
    public HullRating? Rating { get; set; }
    public ICollection<FoulingObservation> Fouling { get; set; } = [];
    public string? Notes { get; set; }
}
