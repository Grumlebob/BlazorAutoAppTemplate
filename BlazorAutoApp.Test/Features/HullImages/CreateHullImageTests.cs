using System;
using System.Net;
using System.Net.Http;
using System.Linq;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.HullImages;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.HullImages;

[Collection("MediaTestCollection")]
public class CreateHullImageTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly AppDbContext _db;

    public CreateHullImageTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        var scope = factory.Services.CreateScope();
        _db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    }

    [Fact]
    public async Task Tus_Upload_And_Download_Works()
    {
        var original = TestImageProvider.GetBytes();

        // TUS create
        using var create = new HttpRequestMessage(HttpMethod.Post, "/api/hull-images/tus");
        create.Headers.Add("Tus-Resumable", "1.0.0");
        create.Headers.Add("Upload-Length", original.Length.ToString());
        var b64name = Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes("test-image.PNG"));
        var b64type = Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes("image/png"));
        create.Headers.Add("Upload-Metadata", $"filename {b64name},contentType {b64type}");
        create.Content = new ByteArrayContent(Array.Empty<byte>());
        var createRes = await _client.SendAsync(create);
        Assert.Equal(HttpStatusCode.Created, createRes.StatusCode);
        var location = createRes.Headers.Location?.ToString() ?? createRes.Headers.GetValues("Location").FirstOrDefault();
        Assert.False(string.IsNullOrWhiteSpace(location));

        // Single PATCH
        using (var patch = new HttpRequestMessage(new HttpMethod("PATCH"), location))
        {
            patch.Headers.Add("Tus-Resumable", "1.0.0");
            patch.Headers.Add("Upload-Offset", "0");
            var body = new ByteArrayContent(original);
            body.Headers.ContentType = new MediaTypeHeaderValue("application/offset+octet-stream");
            patch.Content = body;
            var res = await _client.SendAsync(patch);
            Assert.Equal((HttpStatusCode)204, res.StatusCode);
        }

        // Verify persisted item
        var list = await _client.GetFromJsonAsync<GetHullImagesResponse>("/api/hull-images");
        Assert.NotNull(list);
        var created = list!.Items.First();
        var persisted = await _db.HullImages.FindAsync(created.Id);
        Assert.NotNull(persisted);

        // Download full
        var bytes = await _client.GetByteArrayAsync($"/api/hull-images/{created.Id}/original");
        Assert.Equal(original, bytes);

        // Range request
        var rangeReq = new HttpRequestMessage(HttpMethod.Get, $"/api/hull-images/{created.Id}/original");
        rangeReq.Headers.Range = new RangeHeaderValue(0, 9);
        var rangeRes = await _client.SendAsync(rangeReq);
        Assert.Equal(HttpStatusCode.PartialContent, rangeRes.StatusCode);
        var head = await rangeRes.Content.ReadAsByteArrayAsync();
        Assert.Equal(10, head.Length);
        for (int i = 0; i < 10; i++) Assert.Equal(original[i], head[i]);

        // Delete
        var del = await _client.DeleteAsync($"/api/hull-images/{created.Id}");
        Assert.Equal(HttpStatusCode.NoContent, del.StatusCode);
        var gone = await _client.GetAsync($"/api/hull-images/{created.Id}/original");
        Assert.Equal(HttpStatusCode.NotFound, gone.StatusCode);
    }

    public Task InitializeAsync() => Task.CompletedTask;
    public Task DisposeAsync() => _resetDatabase();
    public void Dispose()
    {
        _db?.Dispose();
        GC.SuppressFinalize(this);
    }
}
