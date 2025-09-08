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
    public async Task List_Returns_Items_After_Upload()
    {
        var sample = TestImageProvider.GetBytes();
        using var content = new ByteArrayContent(sample);
        content.Headers.ContentType = new MediaTypeHeaderValue("image/png");
        using var req = new HttpRequestMessage(HttpMethod.Post, "/api/hull-images") { Content = content };
        req.Headers.Add("X-File-Name", "test-image.PNG");
        var post = await _client.SendAsync(req);
        Assert.Equal(HttpStatusCode.Created, post.StatusCode);

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
