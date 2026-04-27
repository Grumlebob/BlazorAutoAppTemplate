namespace BlazorAutoApp.Core.Features.Inspections.HullImages;

public class GetHullImagesRequest
{
    public int? VesselPartId { get; set; }
}

public class GetHullImagesResponse
{
    public required List<HullImage> Items { get; init; }
}

