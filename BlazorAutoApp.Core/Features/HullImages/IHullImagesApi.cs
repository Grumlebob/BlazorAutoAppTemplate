using System.IO;

namespace BlazorAutoApp.Core.Features.HullImages;

public interface IHullImagesApi
{
    Task<GetHullImagesResponse> GetAsync(GetHullImagesRequest req);
    Task<GetHullImageResponse?> GetByIdAsync(GetHullImageRequest req);
    Task<GetHullImageResponse?> GetByCorrelationIdAsync(Guid correlationId, CancellationToken ct = default);
    Task<CreateHullImageResponse> CreateAsync(CreateHullImageRequest req);

    // Resumable upload (TUS)
    Task UploadTusAsync(string fileName, string? contentType, Stream content, long size, IProgress<long>? progress = null, Guid? correlationId = null, CancellationToken ct = default);

    Task<bool> DeleteAsync(int id, CancellationToken ct = default);
    Task<int> PruneMissingAsync(CancellationToken ct = default);

    // Dev tools: list server static test assets under wwwroot/test-assets
    Task<IReadOnlyList<string>> ListTestAssetsAsync(CancellationToken ct = default);
}
