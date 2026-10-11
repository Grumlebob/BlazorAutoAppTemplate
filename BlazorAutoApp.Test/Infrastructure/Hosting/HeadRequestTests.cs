using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

[Collection(TestCollectionNames.Integration)]
public sealed class HeadRequestTests(WebAppFactory factory)
{
    private readonly HttpClient _client = factory.HttpClient;

    [Fact]
    public async Task HeadHome_UsesGetRouteStatusWithoutBody()
    {
        using var request = new HttpRequestMessage(HttpMethod.Head, "/");
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("text/html"));

        using var response = await _client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Empty(await response.Content.ReadAsByteArrayAsync());
    }

    [Fact]
    public async Task HeadMissingPage_StillReturnsNotFound()
    {
        using var request = new HttpRequestMessage(HttpMethod.Head, "/missing-head-page");

        using var response = await _client.SendAsync(request);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }
}
