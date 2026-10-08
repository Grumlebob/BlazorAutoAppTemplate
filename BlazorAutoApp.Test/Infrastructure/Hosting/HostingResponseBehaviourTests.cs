using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

public sealed class HostingResponseBehaviourTests(HostingResponseBehaviourFixture fixture)
    : IClassFixture<HostingResponseBehaviourFixture>
{
    [Fact]
    public async Task StaticAssets_DoNotReturnTooManyRequests_WhenGlobalLimitIsExceeded()
    {
        const string forwardedIp = "203.0.113.12";

        for (var requestNumber = 1; requestNumber <= HostingResponseBehaviourFixture.GlobalPermitLimit + 1; requestNumber++)
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, "/");
            request.Headers.TryAddWithoutValidation("X-Forwarded-For", forwardedIp);

            using var response = await fixture.Factory.HttpClient.SendAsync(request);

            if (requestNumber <= HostingResponseBehaviourFixture.GlobalPermitLimit)
            {
                Assert.NotEqual(HttpStatusCode.TooManyRequests, response.StatusCode);
            }
            else
            {
                Assert.Equal(HttpStatusCode.TooManyRequests, response.StatusCode);
            }
        }

        for (var requestNumber = 1; requestNumber <= HostingResponseBehaviourFixture.GlobalPermitLimit + 2; requestNumber++)
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, "/app.css");
            request.Headers.TryAddWithoutValidation("X-Forwarded-For", forwardedIp);

            using var response = await fixture.Factory.HttpClient.SendAsync(request);

            Assert.NotEqual(HttpStatusCode.TooManyRequests, response.StatusCode);
        }
    }

    [Fact]
    public async Task Api_AnonymousRequest_WithIdentityCookieChallenge_Returns401NotRedirect()
    {
        using var client = fixture.Factory.CreateClient(new Microsoft.AspNetCore.Mvc.Testing.WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false
        });
        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/books");
        request.Headers.TryAddWithoutValidation("X-Forwarded-For", "203.0.113.13");

        using var response = await client.SendAsync(request);
        var body = await response.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Null(response.Headers.Location);
        Assert.DoesNotContain("<html", body, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task UserSpecificApiResponses_AreNotCacheable()
    {
        using var client = fixture.Factory.CreateAuthenticatedClient($"cache-headers-{Guid.NewGuid():N}@example.test");
        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/books");
        request.Headers.TryAddWithoutValidation("X-Forwarded-For", "203.0.113.14");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(response.Headers.CacheControl);
        Assert.True(response.Headers.CacheControl!.Private);
        Assert.True(response.Headers.CacheControl.NoStore);
        Assert.Contains("no-cache", response.Headers.Pragma.Select(value => value.Name));
    }
}

public sealed class HostingResponseBehaviourFixture : IAsyncLifetime
{
    public const int GlobalPermitLimit = 5;

    public WebAppFactory Factory { get; } = new(new WebAppFactoryOptions
    {
        GlobalRateLimitPermitLimit = GlobalPermitLimit,
        UseIdentityCookieChallenge = true
    });

    public async ValueTask InitializeAsync()
    {
        await Factory.InitializeAsync();
    }

    public async ValueTask DisposeAsync()
    {
        await Factory.DisposeAsync();
    }
}
