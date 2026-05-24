using BlazorAutoApp.Core.Features.Inspections.HullImages.Domain;

namespace BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.GetHullImages;

public class GetHullImagesResponse
{
    public required List<HullImage> Items { get; init; }
}
