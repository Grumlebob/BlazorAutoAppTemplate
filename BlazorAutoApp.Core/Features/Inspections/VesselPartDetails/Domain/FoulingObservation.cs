namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;

public class FoulingObservation
{
    public int Id { get; set; }
    public required int VesselPartDetailsId { get; set; }
    public FoulingType FoulingType { get; set; }
    public bool IsPresent { get; set; }
    public int? CoveragePercent { get; set; }
}
