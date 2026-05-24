using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;

namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Contracts;

public class HullRatingDto
{
    public HullRatingValue Rating { get; set; }
    public string? Rationale { get; set; }
}
