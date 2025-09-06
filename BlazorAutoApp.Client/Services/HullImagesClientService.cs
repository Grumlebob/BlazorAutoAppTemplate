using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.HullImages;
using BlazorAutoApp.Client.Services.Http;

namespace BlazorAutoApp.Client.Services;

public class HullImagesClientService(HttpClient http) : IHullImagesApi
{
    private readonly HttpClient _http = http;

    public async Task<GetHullImagesResponse> GetAsync(GetHullImagesRequest req)
    {
        var res = await _http.GetFromJsonAsync<GetHullImagesResponse>("api/hull-images");
        return res ?? new GetHullImagesResponse { Items = new() };
    }

    public async Task<CreateHullImageResponse> CreateAsync(CreateHullImageRequest req)
    {
        var response = await _http.PostAsJsonAsync("api/hull-images/metadata", req);
        response.EnsureSuccessStatusCode();
        var created = await response.Content.ReadFromJsonAsync<CreateHullImageResponse>();
        return created!;
    }

    public async Task<GetHullImageResponse?> GetByIdAsync(GetHullImageRequest req)
    {
        return await _http.GetFromJsonAsync<GetHullImageResponse>($"api/hull-images/{req.Id}");
    }

    public async Task<CreateHullImageResponse> UploadAsync(string fileName, string? contentType, Stream content, long? size, IProgress<long>? progress, CancellationToken ct = default)
    {
        var progressContent = new ProgressStreamContent(
            content,
            bufferSize: 128 * 1024,
            progress: uploaded => progress?.Report(uploaded),
            contentType: string.IsNullOrWhiteSpace(contentType) ? "application/octet-stream" : contentType,
            contentLength: size);

        using var req = new HttpRequestMessage(HttpMethod.Post, "api/hull-images") { Content = progressContent };
        req.Headers.Add("X-File-Name", fileName);
        var res = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        res.EnsureSuccessStatusCode();
        var created = await res.Content.ReadFromJsonAsync<CreateHullImageResponse>(cancellationToken: ct);
        return created!;
    }

    public async Task<InitiateHullImageUploadResponse> InitiateUploadAsync(string fileName, string? contentType, CancellationToken ct = default)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, "api/hull-images/uploads");
        req.Headers.Add("X-File-Name", fileName);
        req.Headers.Add("X-Content-Type", string.IsNullOrWhiteSpace(contentType) ? "application/octet-stream" : contentType);
        var res = await _http.SendAsync(req, ct);
        res.EnsureSuccessStatusCode();
        var payload = await res.Content.ReadFromJsonAsync<InitiateHullImageUploadResponse>(cancellationToken: ct);
        return payload!;
    }

    public async Task UploadChunkAsync(Guid sessionId, int index, Stream chunk, CancellationToken ct = default)
    {
        using var ms = new MemoryStream();
        await chunk.CopyToAsync(ms, ct);
        ms.Position = 0;
        using var content = new StreamContent(ms);
        var res = await _http.PutAsync($"api/hull-images/uploads/{sessionId}/chunks/{index}", content, ct);
        res.EnsureSuccessStatusCode();
    }

    public async Task<CreateHullImageResponse> CompleteUploadAsync(Guid sessionId, CancellationToken ct = default)
    {
        var res = await _http.PostAsync($"api/hull-images/uploads/{sessionId}/complete", content: null, ct);
        res.EnsureSuccessStatusCode();
        var created = await res.Content.ReadFromJsonAsync<CreateHullImageResponse>(cancellationToken: ct);
        return created!;
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken ct = default)
    {
        var res = await _http.DeleteAsync($"api/hull-images/{id}", ct);
        return res.IsSuccessStatusCode;
    }

    public async Task<int> PruneMissingAsync(CancellationToken ct = default)
    {
        var res = await _http.PostAsync("api/hull-images/prune-missing", content: null, ct);
        res.EnsureSuccessStatusCode();
        var payload = await res.Content.ReadFromJsonAsync<Dictionary<string, int>>(cancellationToken: ct);
        return payload is not null && payload.TryGetValue("removed", out var removed) ? removed : 0;
    }
}
