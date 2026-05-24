using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Contracts;

namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.UseCases.GetVesselPartDetails;

public class GetVesselPartDetailsResponse
{
    public required int InspectionVesselPartId { get; init; }
    public bool HasSaved { get; init; }
    public List<FoulingObservationDto> Fouling { get; init; } = [];
    public CoatingConditionDto Coating { get; init; } = new();
    public HullConditionDto Hull { get; init; } = new();
    public HullRatingDto Rating { get; init; } = new();
    public string? Notes { get; init; }
}
