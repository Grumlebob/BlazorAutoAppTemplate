namespace BlazorAutoApp.Core.Features.HullImages;

public class GetHullImagesRequest
{
}

public class GetHullImagesResponse
{
    public required List<HullImage> Items { get; init; }
}

