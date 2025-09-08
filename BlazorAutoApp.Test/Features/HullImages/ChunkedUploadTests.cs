using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.HullImages;
using BlazorAutoApp.Test.TestingSetup;
using Xunit;

namespace BlazorAutoApp.Test.Features.HullImages;

[Collection("MediaTestCollection")]
public class ChunkedUploadTests : IAsyncLifetime
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;

    public ChunkedUploadTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
    }

    [Fact]
    public async Task Tus_Upload_And_Download_Matches()
    {
        var all = TestImageProvider.GetBytes();
        var split1 = Math.Min(10, all.Length);
        var split2 = Math.Min(split1 + Math.Max(1, all.Length / 2), all.Length);
        var chunks = new[]
        {
            all[..split1],
            all[split1..split2],
            all[split2..]
        };
        var total = all.Length;

        // TUS create
        var create = new HttpRequestMessage(HttpMethod.Post, "/api/hull-images/tus");
        create.Headers.Add("Tus-Resumable", "1.0.0");
        create.Headers.Add("Upload-Length", total.ToString());
        var b64name = Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes("test-image.PNG"));
        var b64type = Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes("image/png"));
        create.Headers.Add("Upload-Metadata", $"filename {b64name},contentType {b64type}");
        create.Content = new ByteArrayContent(Array.Empty<byte>());
        var createRes = await _client.SendAsync(create);
        Assert.Equal(HttpStatusCode.Created, createRes.StatusCode);
        var location = createRes.Headers.Location?.ToString() ?? createRes.Headers.GetValues("Location").FirstOrDefault();
        Assert.False(string.IsNullOrWhiteSpace(location));

        // Send PATCH chunks
        long offset = 0;
        foreach (var part in chunks)
        {
            var patch = new HttpRequestMessage(new HttpMethod("PATCH"), location);
            patch.Headers.Add("Tus-Resumable", "1.0.0");
            patch.Headers.Add("Upload-Offset", offset.ToString());
            var content = new ByteArrayContent(part);
            content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/offset+octet-stream");
            patch.Content = content;
            var res = await _client.SendAsync(patch);
            Assert.Equal((HttpStatusCode)204, res.StatusCode);
            if (res.Headers.TryGetValues("Upload-Offset", out var offsets) && long.TryParse(offsets.FirstOrDefault(), out var newOffset))
                offset = newOffset;
            else
                offset += part.Length;
        }
        Assert.Equal(total, offset);

        // Give the server a brief moment to finalize (usually synchronous)
        await Task.Delay(50);

        // Verify by listing and downloading
        var list = await _client.GetFromJsonAsync<GetHullImagesResponse>("/api/hull-images");
        Assert.NotNull(list);
        Assert.True(list!.Items.Count > 0);
        var created = list.Items.First();

        var bytes = await _client.GetByteArrayAsync($"/api/hull-images/{created!.Id}/original");
        Assert.Equal(all.Length, bytes.Length);
        Assert.Equal(all, bytes);
    }

    public Task InitializeAsync() => Task.CompletedTask;
    public Task DisposeAsync() => _resetDatabase();
}
