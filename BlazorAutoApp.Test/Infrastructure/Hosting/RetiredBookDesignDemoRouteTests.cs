using System;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

[Collection(TestCollectionNames.Integration)]
[Trait("FrontendProfile", "BlazorAuto")]
public sealed class RetiredBookDesignDemoRouteTests(WebAppFactory factory)
{
    private readonly HttpClient _client = factory.HttpClient;

    [Theory]
    [InlineData("GET", "/books/design-demos")]
    [InlineData("GET", "/books/design-demos/cloth-hardback")]
    [InlineData("HEAD", "/books/design-demos")]
    [InlineData("HEAD", "/books/design-demos/cloth-hardback")]
    public async Task RetiredDesignDemoRoutes_ReturnNotFoundForGetAndHead(string method, string path)
    {
        foreach (var query in new[] { string.Empty, "?open=true" })
        {
            using var request = new HttpRequestMessage(new HttpMethod(method), path + query);
            using var response = await _client.SendAsync(request);

            Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
            if (string.Equals(method, HttpMethod.Head.Method, StringComparison.Ordinal))
            {
                Assert.Empty(await response.Content.ReadAsByteArrayAsync());
            }
        }
    }
}
