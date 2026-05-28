using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

[Collection("IntegrationTestCollection")]
public sealed class HeadRequestTests(WebAppFactory factory)
{
    private readonly HttpClient _client = factory.HttpClient;

    [Fact]
    public async Task HeadHome_UsesGetRouteStatusWithoutBody()
    {
        using var request = new HttpRequestMessage(HttpMethod.Head, "/");

        using var response = await _client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(0, response.Content.Headers.ContentLength ?? 0);
    }

    [Fact]
    public async Task HeadMissingPage_StillReturnsNotFound()
    {
        using var request = new HttpRequestMessage(HttpMethod.Head, "/missing-head-page");

        using var response = await _client.SendAsync(request);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }
}
