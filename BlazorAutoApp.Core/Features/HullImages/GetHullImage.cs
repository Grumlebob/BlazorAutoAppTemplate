namespace BlazorAutoApp.Core.Features.HullImages;

public class GetHullImageRequest
{
    public int Id { get; set; }
}

public class GetHullImageResponse
{
    public int Id { get; init; }
    public required string OriginalFileName { get; init; }
    public string? ContentType { get; init; }
    public long ByteSize { get; init; }
    public string? Sha256 { get; init; }
    public int? Width { get; init; }
    public int? Height { get; init; }
    public DateTime CreatedAtUtc { get; init; }
    public double AiHullScore { get; init; }
    public string VesselName { get; init; } = "BoatyBoat";
    public int? InspectionVesselPartId { get; init; }
}

