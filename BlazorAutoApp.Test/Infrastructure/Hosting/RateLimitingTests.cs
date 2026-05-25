using System;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

[Collection("IntegrationTestCollection")]
public sealed class RateLimitingTests(WebAppFactory factory)
{
    private const int ApiPermitLimit = 60;
    private const int AuthenticationPermitLimit = 20;

    private readonly HttpClient _client = factory.HttpClient;

    [Fact]
    public async Task MoviesApi_ReturnsTooManyRequests_WhenApiLimitIsExceeded()
    {
        var forwardedIp = $"203.0.113.{Random.Shared.Next(1, 255)}";
        var lastStatusCode = HttpStatusCode.OK;
        var lastResponseHadRetryAfter = false;

        for (var requestNumber = 1; requestNumber <= ApiPermitLimit + 1; requestNumber++)
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, "/api/movies");
            request.Headers.TryAddWithoutValidation("X-Forwarded-For", forwardedIp);

            using var response = await _client.SendAsync(request);
            lastStatusCode = response.StatusCode;
            lastResponseHadRetryAfter = response.Headers.RetryAfter is not null;

            if (requestNumber <= ApiPermitLimit)
            {
                Assert.NotEqual(HttpStatusCode.TooManyRequests, response.StatusCode);
            }
        }

        Assert.Equal(HttpStatusCode.TooManyRequests, lastStatusCode);
        Assert.True(lastResponseHadRetryAfter);
    }

    [Fact]
    public async Task AccountPost_ReturnsTooManyRequests_WhenAuthenticationLimitIsExceeded()
    {
        var forwardedIp = $"203.0.113.{Random.Shared.Next(1, 255)}";
        var lastStatusCode = HttpStatusCode.OK;
        var lastResponseHadRetryAfter = false;

        for (var requestNumber = 1; requestNumber <= AuthenticationPermitLimit + 1; requestNumber++)
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, "/Account/Login");
            request.Headers.TryAddWithoutValidation("X-Forwarded-For", forwardedIp);
            request.Content = new FormUrlEncodedContent([]);

            using var response = await _client.SendAsync(request);
            lastStatusCode = response.StatusCode;
            lastResponseHadRetryAfter = response.Headers.RetryAfter is not null;

            if (requestNumber <= AuthenticationPermitLimit)
            {
                Assert.NotEqual(HttpStatusCode.TooManyRequests, response.StatusCode);
            }
        }

        Assert.Equal(HttpStatusCode.TooManyRequests, lastStatusCode);
        Assert.True(lastResponseHadRetryAfter);
    }
}
