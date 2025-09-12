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

namespace BlazorAutoApp.Test.Features.Inspections.HullImages;

[Collection("MediaTestCollection")]
public class GetHullImagesTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly AppDbContext _db;

    public GetHullImagesTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        var scope = factory.Services.CreateScope();
        _db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    }

    [Fact]
    public async Task List_Returns_Items_After_Tus_Upload()
    {
        var sample = TestImageProvider.GetBytes();
        // TUS create
        using var create = new HttpRequestMessage(HttpMethod.Post, "/api/hull-images/tus");
        create.Headers.Add("Tus-Resumable", "1.0.0");
        create.Headers.Add("Upload-Length", sample.Length.ToString());
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
            var body = new ByteArrayContent(sample);
            body.Headers.ContentType = new MediaTypeHeaderValue("application/offset+octet-stream");
            patch.Content = body;
            var res = await _client.SendAsync(patch);
            Assert.Equal((HttpStatusCode)204, res.StatusCode);
        }

        var list = await _client.GetFromJsonAsync<GetHullImagesResponse>("/api/hull-images");
        Assert.NotNull(list);
        Assert.True(list!.Items.Count >= 1);
        Assert.Contains(list.Items, i => i.OriginalFileName == "test-image.PNG");
    }

    public Task InitializeAsync() => Task.CompletedTask;
    public Task DisposeAsync() => _resetDatabase();
    public void Dispose()
    {
        _db?.Dispose();
        GC.SuppressFinalize(this);
    }
}
