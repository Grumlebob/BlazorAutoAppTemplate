namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;

public class HullRating
{
    public int Id { get; set; }
    public required int VesselPartDetailsId { get; set; }
    public HullRatingValue Rating { get; set; }
    public string? Rationale { get; set; }
}
