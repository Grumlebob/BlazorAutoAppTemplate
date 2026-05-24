using System.ComponentModel.DataAnnotations;
using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Contracts;

namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.UseCases.UpsertVesselPartDetails;

public class UpsertVesselPartDetailsRequest
{
    public required int InspectionVesselPartId { get; init; }
    public List<FoulingObservationDto> Fouling { get; init; } = [];
    public required CoatingConditionDto Coating { get; init; } = new();
    public required HullConditionDto Hull { get; init; } = new();
    public required HullRatingDto Rating { get; init; } = new();

    [StringLength(4000)]
    public string? Notes { get; init; }
}
