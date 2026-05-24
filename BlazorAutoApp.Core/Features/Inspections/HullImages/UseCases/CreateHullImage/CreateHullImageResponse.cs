namespace BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.CreateHullImage;

public class CreateHullImageResponse
{
    public int Id { get; init; }
    public required string OriginalFileName { get; init; }
    public string? ContentType { get; init; }
    public long ByteSize { get; init; }
    public string? Sha256 { get; init; }
    public int? Width { get; init; }
    public int? Height { get; init; }
    public string VesselName { get; init; } = "BoatyBoat";
    public int? InspectionVesselPartId { get; init; }
}
