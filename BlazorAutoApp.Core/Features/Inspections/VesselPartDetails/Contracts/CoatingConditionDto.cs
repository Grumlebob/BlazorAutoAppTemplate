using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Contracts;

public class CoatingConditionDto
{
    [Range(0, 100)]
    public int IntactPercent { get; set; }
    public bool Peeling { get; set; }
    public bool Blisters { get; set; }
    public bool Scratching { get; set; }
}
