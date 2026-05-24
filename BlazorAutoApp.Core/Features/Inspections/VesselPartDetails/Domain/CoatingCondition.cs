namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;

public class CoatingCondition
{
    public int Id { get; set; }
    public required int VesselPartDetailsId { get; set; }
    public int IntactPercent { get; set; }
    public bool Peeling { get; set; }
    public bool Blisters { get; set; }
    public bool Scratching { get; set; }
}
