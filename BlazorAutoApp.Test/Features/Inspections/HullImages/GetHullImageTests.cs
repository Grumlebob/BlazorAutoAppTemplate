using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Inspections.HullImages.Contracts;
using BlazorAutoApp.Core.Features.Inspections.HullImages.Domain;
using BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.CreateHullImage;
using BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.GetHullImage;
using BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.GetHullImages;
using BlazorAutoApp.Test.TestingSetup;
using Xunit;

namespace BlazorAutoApp.Test.Features.Inspections.HullImages;

[Collection("MediaTestCollection")]
public class GetHullImageTests(WebAppFactory factory) : IAsyncLifetime
{
    private readonly HttpClient _client = factory.HttpClient;
    private readonly Func<Task> _reset = factory.ResetDatabaseAsync;

    [Fact]
    public async Task GetById_Returns_404_When_NotFound()
    {
        var res = await _client.GetAsync("/api/hull-images/999999");
        Assert.Equal(HttpStatusCode.NotFound, res.StatusCode);
    }

    public ValueTask InitializeAsync() => ValueTask.CompletedTask;
    public async ValueTask DisposeAsync() => await _reset();
}

