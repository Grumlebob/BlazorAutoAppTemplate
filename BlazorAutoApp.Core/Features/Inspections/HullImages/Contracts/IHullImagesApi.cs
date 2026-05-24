using BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.CreateHullImage;
using BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.GetHullImage;
using BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.GetHullImages;

namespace BlazorAutoApp.Core.Features.Inspections.HullImages.Contracts;

public interface IHullImagesApi
{
    Task<GetHullImagesResponse> GetAsync(GetHullImagesRequest req);
    Task<GetHullImageResponse?> GetByIdAsync(GetHullImageRequest req);
    Task<GetHullImageResponse?> GetByCorrelationIdAsync(Guid correlationId, CancellationToken ct = default);
    Task<CreateHullImageResponse> CreateAsync(CreateHullImageRequest req);
    Task UploadTusAsync(string fileName, string? contentType, Stream content, long size, IProgress<long>? progress = null, Guid? correlationId = null, CancellationToken ct = default);
    Task<bool> DeleteAsync(int id, CancellationToken ct = default);
    Task<int> PruneMissingAsync(CancellationToken ct = default);
}
