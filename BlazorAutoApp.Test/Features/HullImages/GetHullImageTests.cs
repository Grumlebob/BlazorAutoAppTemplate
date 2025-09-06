using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.HullImages;
using BlazorAutoApp.Test.TestingSetup;
using Xunit;

namespace BlazorAutoApp.Test.Features.HullImages;

[Collection("MediaTestCollection")]
public class GetHullImageTests : IAsyncLifetime
{
    private readonly HttpClient _client;
    private readonly Func<Task> _reset;

    public GetHullImageTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _reset = factory.ResetDatabaseAsync;
    }

    [Fact]
    public async Task GetById_Returns_404_When_NotFound()
    {
        var res = await _client.GetAsync("/api/hull-images/999999");
        Assert.Equal(HttpStatusCode.NotFound, res.StatusCode);
    }

    public Task InitializeAsync() => Task.CompletedTask;
    public Task DisposeAsync() => _reset();
}
