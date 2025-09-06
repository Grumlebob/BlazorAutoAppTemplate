using System.IO;

namespace BlazorAutoApp.Core.Features.HullImages;

public record InitiateHullImageUploadResponse(Guid UploadSessionId, int ChunkSizeBytes);

public interface IHullImagesApi
{
    Task<GetHullImagesResponse> GetAsync(GetHullImagesRequest req);
    Task<GetHullImageResponse?> GetByIdAsync(GetHullImageRequest req);
    Task<CreateHullImageResponse> CreateAsync(CreateHullImageRequest req);

    // Single-shot streaming upload
    Task<CreateHullImageResponse> UploadAsync(string fileName, string? contentType, Stream content, long? size, IProgress<long>? progress, CancellationToken ct = default);

    // Simple chunked upload
    Task<InitiateHullImageUploadResponse> InitiateUploadAsync(string fileName, string? contentType, CancellationToken ct = default);
    Task UploadChunkAsync(Guid sessionId, int index, Stream chunk, CancellationToken ct = default);
    Task<CreateHullImageResponse> CompleteUploadAsync(Guid sessionId, CancellationToken ct = default);

    Task<bool> DeleteAsync(int id, CancellationToken ct = default);
    Task<int> PruneMissingAsync(CancellationToken ct = default);
}
