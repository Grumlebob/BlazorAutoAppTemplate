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
