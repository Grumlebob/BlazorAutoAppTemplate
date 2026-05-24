namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;

public class HullCondition
{
    public int Id { get; set; }
    public required int VesselPartDetailsId { get; set; }
    public int IntegrityPercent { get; set; }
    public bool Corrosion { get; set; }
    public bool Dents { get; set; }
    public bool Cracks { get; set; }
}
