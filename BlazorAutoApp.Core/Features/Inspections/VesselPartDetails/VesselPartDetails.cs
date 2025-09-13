using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails;

public enum FoulingType
{
    Slime = 0,
    Algae = 1,
    Grass = 2,
    Barnacles = 3,
    Mussels = 4,
    Tubeworms = 5
}

public enum HullRatingValue
{
    Clean = 0,
    Light = 1,
    Medium = 2,
    Heavy = 3,
    VeryHeavy = 4
}

// Entities (persisted)
public class VesselPartDetails
{
    public int Id { get; set; }
    public required int InspectionVesselPartId { get; set; }

    public CoatingCondition? Coating { get; set; }
    public HullCondition? Hull { get; set; }
    public HullRating? Rating { get; set; }
    public ICollection<FoulingObservation> Fouling { get; set; } = new List<FoulingObservation>();
    public string? Notes { get; set; }
}

public class FoulingObservation
{
    public int Id { get; set; }
    public required int VesselPartDetailsId { get; set; }
    public FoulingType FoulingType { get; set; }
    public bool IsPresent { get; set; }
    public int? CoveragePercent { get; set; } // 0-100 when IsPresent
}

public class CoatingCondition
{
    public int Id { get; set; }
    public required int VesselPartDetailsId { get; set; }
    public int IntactPercent { get; set; } // 0-100
    public bool Peeling { get; set; }
    public bool Blisters { get; set; }
    public bool Scratching { get; set; }
}

public class HullCondition
{
    public int Id { get; set; }
    public required int VesselPartDetailsId { get; set; }
    public int IntegrityPercent { get; set; } // 0-100
    public bool Corrosion { get; set; }
    public bool Dents { get; set; }
    public bool Cracks { get; set; }
}

public class HullRating
{
    public int Id { get; set; }
    public required int VesselPartDetailsId { get; set; }
    public HullRatingValue Rating { get; set; }
    public string? Rationale { get; set; }
}

// DTOs for transport
public class GetVesselPartDetailsResponse
{
    public required int InspectionVesselPartId { get; init; }
    public List<FoulingObservationDto> Fouling { get; init; } = new();
    public CoatingConditionDto Coating { get; init; } = new();
    public HullConditionDto Hull { get; init; } = new();
    public HullRatingDto Rating { get; init; } = new();
    public string? Notes { get; init; }
}

public class UpsertVesselPartDetailsRequest
{
    public required int InspectionVesselPartId { get; init; }
    public List<FoulingObservationDto> Fouling { get; init; } = new();
    public required CoatingConditionDto Coating { get; init; } = new();
    public required HullConditionDto Hull { get; init; } = new();
    public required HullRatingDto Rating { get; init; } = new();
    [StringLength(4000)]
    public string? Notes { get; init; }
}

public class UpsertVesselPartDetailsResponse
{
    public bool Success { get; set; }
    public string? Error { get; set; }
}

public class FoulingObservationDto : IValidatableObject
{
    public FoulingType FoulingType { get; set; }
    public bool IsPresent { get; set; }
    [Range(0,100)]
    public int? CoveragePercent { get; set; }

    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        if (IsPresent && CoveragePercent is null)
        {
            yield return new ValidationResult("Coverage is required when fouling is selected.", new[] { nameof(CoveragePercent) });
        }
        if (CoveragePercent is int v && (v < 0 || v > 100))
        {
            yield return new ValidationResult("Coverage must be 0-100.", new[] { nameof(CoveragePercent) });
        }
    }
}

public class CoatingConditionDto
{
    [Range(0,100)]
    public int IntactPercent { get; set; }
    public bool Peeling { get; set; }
    public bool Blisters { get; set; }
    public bool Scratching { get; set; }
}

public class HullConditionDto
{
    [Range(0,100)]
    public int IntegrityPercent { get; set; }
    public bool Corrosion { get; set; }
    public bool Dents { get; set; }
    public bool Cracks { get; set; }
}

public class HullRatingDto
{
    public HullRatingValue Rating { get; set; }
    public string? Rationale { get; set; }
}

public interface IVesselPartDetailsApi
{
    Task<GetVesselPartDetailsResponse> GetAsync(int vesselPartId, CancellationToken ct = default);
    Task<UpsertVesselPartDetailsResponse> UpsertAsync(UpsertVesselPartDetailsRequest req, CancellationToken ct = default);
}
