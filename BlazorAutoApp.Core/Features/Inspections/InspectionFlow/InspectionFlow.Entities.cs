using BlazorAutoApp.Core.Features.Inspections.HullImages;

namespace BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

public enum InspectionType
{
    GoProInspection = 0,
    DivingInspection = 1,
    ROVInspection = 2,
    HullCleaning = 3,
    PropellerCleaning = 4
}

public class InspectionFlow
{
    public Guid Id { get; set; } // same as Inspection.Inspection.Id
    public string? VesselName { get; set; }
    public InspectionType InspectionType { get; set; }
    public List<InspectionVesselPart> VesselParts { get; set; } = [];
}

public class InspectionVesselPart
{
    public int Id { get; set; }
    public Guid InspectionId { get; set; }
    public required string PartCode { get; set; }
    public ICollection<HullImage> HullImages { get; set; } = [];
}

public class Vessel
{
    public int Id { get; set; }
    public required string Name { get; set; }
}
