using System.ComponentModel.DataAnnotations;
using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;

namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Contracts;

public class FoulingObservationDto : IValidatableObject
{
    public FoulingType FoulingType { get; set; }
    public bool IsPresent { get; set; }

    [Range(0, 100)]
    public int? CoveragePercent { get; set; }

    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        if (IsPresent && CoveragePercent is null)
        {
            yield return new ValidationResult("Coverage is required when fouling is selected.", [nameof(CoveragePercent)]);
        }
        if (CoveragePercent is int v && (v < 0 || v > 100))
        {
            yield return new ValidationResult("Coverage must be 0-100.", [nameof(CoveragePercent)]);
        }
    }
}
