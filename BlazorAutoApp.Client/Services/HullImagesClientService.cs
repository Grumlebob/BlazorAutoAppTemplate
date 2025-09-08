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

    public async Task<GetHullImageResponse?> GetByCorrelationIdAsync(Guid correlationId, CancellationToken ct = default)
    {
        var url = $"api/hull-images/tus/result?correlationId={Uri.EscapeDataString(correlationId.ToString())}";
        var res = await _http.GetAsync(url, ct);
        if (res.StatusCode == System.Net.HttpStatusCode.NotFound) return null;
        res.EnsureSuccessStatusCode();
        return await res.Content.ReadFromJsonAsync<GetHullImageResponse>(cancellationToken: ct);
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

    public async Task UploadTusAsync(string fileName, string? contentType, Stream content, long size, IProgress<long>? progress = null, Guid? correlationId = null, CancellationToken ct = default)
    {
        using var create = new HttpRequestMessage(HttpMethod.Post, "api/hull-images/tus");
        create.Headers.TryAddWithoutValidation("Tus-Resumable", "1.0.0");
        create.Headers.TryAddWithoutValidation("Upload-Length", size.ToString());
        var metadata = $"filename {ToB64(fileName)},contentType {ToB64(string.IsNullOrWhiteSpace(contentType) ? "application/octet-stream" : contentType!)}";
        if (correlationId is Guid c)
        {
            metadata += $",correlationId {ToB64(c.ToString())}";
        }
        create.Headers.TryAddWithoutValidation("Upload-Metadata", metadata);
        create.Content = new ByteArrayContent(Array.Empty<byte>());
        var createRes = await _http.SendAsync(create, ct);
        createRes.EnsureSuccessStatusCode();
        var location = createRes.Headers.Location?.ToString() ?? (createRes.Headers.TryGetValues("Location", out var locs) ? locs.FirstOrDefault() : null);
        if (string.IsNullOrWhiteSpace(location)) throw new InvalidOperationException("No TUS Location returned");
        var uploadUri = location.StartsWith("http", StringComparison.OrdinalIgnoreCase)
            ? new Uri(location)
            : new Uri(_http.BaseAddress!, location);

        const int chunkSize = 4 * 1024 * 1024;
        var buffer = new byte[chunkSize];
        long offset = 0;
        int read;
        while ((read = await content.ReadAsync(buffer, 0, buffer.Length, ct)) > 0)
        {
            using var patch = new HttpRequestMessage(new HttpMethod("PATCH"), uploadUri);
            patch.Headers.TryAddWithoutValidation("Tus-Resumable", "1.0.0");
            patch.Headers.TryAddWithoutValidation("Upload-Offset", offset.ToString());
            var body = new ByteArrayContent(buffer, 0, read);
            body.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/offset+octet-stream");
            patch.Content = body;
            var res = await _http.SendAsync(patch, ct);
            if ((int)res.StatusCode != 204) throw new HttpRequestException($"TUS PATCH failed: {(int)res.StatusCode}");
            if (res.Headers.TryGetValues("Upload-Offset", out var offsets) && long.TryParse(offsets.FirstOrDefault(), out var newOffset))
                offset = newOffset;
            else
                offset += read;
            progress?.Report(offset);
        }
        if (offset != size) throw new InvalidOperationException($"Upload incomplete: {offset}/{size}");
    }

    private static string ToB64(string value) => Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(value ?? string.Empty));

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

    public async Task<IReadOnlyList<string>> ListTestAssetsAsync(CancellationToken ct = default)
    {
        var items = await _http.GetFromJsonAsync<string[]>("api/hull-images/test-assets", cancellationToken: ct);
        return items ?? Array.Empty<string>();
    }
}
