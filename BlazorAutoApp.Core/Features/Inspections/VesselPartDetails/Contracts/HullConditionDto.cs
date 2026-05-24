using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Contracts;

public class HullConditionDto
{
    [Range(0, 100)]
    public int IntegrityPercent { get; set; }
    public bool Corrosion { get; set; }
    public bool Dents { get; set; }
    public bool Cracks { get; set; }
}
