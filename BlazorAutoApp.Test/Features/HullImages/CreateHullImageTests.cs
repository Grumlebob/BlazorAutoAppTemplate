using System;
using System.Net;
using System.Net.Http;
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
    public async Task SingleShot_Upload_And_Download_Works()
    {
        var original = TestImageProvider.GetBytes();
        using var content = new ByteArrayContent(original);
        content.Headers.ContentType = new MediaTypeHeaderValue("image/png");

        using var req = new HttpRequestMessage(HttpMethod.Post, "/api/hull-images") { Content = content };
        req.Headers.Add("X-File-Name", "test-image.PNG");

        var response = await _client.SendAsync(req, HttpCompletionOption.ResponseHeadersRead);
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);

        var payload = await response.Content.ReadFromJsonAsync<CreateHullImageResponse>();
        Assert.NotNull(payload);
        Assert.True(payload!.Id > 0);
        Assert.Equal(original.LongLength, payload.ByteSize);

        var persisted = await _db.HullImages.FindAsync(payload.Id);
        Assert.NotNull(persisted);
        Assert.Equal(original.LongLength, persisted!.ByteSize);

        // Download full
        var bytes = await _client.GetByteArrayAsync($"/api/hull-images/{payload.Id}/original");
        Assert.Equal(original, bytes);

        // Range request
        var rangeReq = new HttpRequestMessage(HttpMethod.Get, $"/api/hull-images/{payload.Id}/original");
        rangeReq.Headers.Range = new RangeHeaderValue(0, 9);
        var rangeRes = await _client.SendAsync(rangeReq);
        Assert.Equal(HttpStatusCode.PartialContent, rangeRes.StatusCode);
        var head = await rangeRes.Content.ReadAsByteArrayAsync();
        Assert.Equal(10, head.Length);
        for (int i = 0; i < 10; i++) Assert.Equal(original[i], head[i]);

        // Delete
        var del = await _client.DeleteAsync($"/api/hull-images/{payload.Id}");
        Assert.Equal(HttpStatusCode.NoContent, del.StatusCode);
        var gone = await _client.GetAsync($"/api/hull-images/{payload.Id}/original");
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
