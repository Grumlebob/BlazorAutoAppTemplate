using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Xunit;

namespace GrumPlates.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountGuardTests
{
    [Fact]
    public async Task PrivateReads_RequireCapturedOwnerAndPreserveUnknownRoute404()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var user = await fixture.CreateUserAsync();
        using var login = await RealCookieAccountFixture.LoginAsync(client, user.Email, user.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        foreach (var expected in new string?[] { null, "another-user", user.Id + "," + user.Id })
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, "/api/books");
            if (expected is not null) request.Headers.Add("X-Expected-User", expected);
            using var response = await client.SendAsync(request);
            Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
            Assert.True(response.Headers.CacheControl?.NoStore);
            var body = await response.Content.ReadAsStringAsync();
            using var problem = JsonDocument.Parse(body);
            Assert.Equal("AccountChanged", problem.RootElement.GetProperty("code").GetString());
            Assert.DoesNotContain(user.Id, body);
            Assert.DoesNotContain("another-user", body);
        }
        client.DefaultRequestHeaders.Add("X-Expected-User", user.Id);
        using var allowed = await client.GetAsync("/api/books");
        Assert.Equal(HttpStatusCode.OK, allowed.StatusCode);
        using var unknown = await client.GetAsync("/api/books/not-an-id");
        Assert.Equal(HttpStatusCode.NotFound, unknown.StatusCode);
        client.DefaultRequestHeaders.Remove("X-Expected-User");
        using var unknownWithoutOwner = await client.GetAsync("/api/books/not-an-id");
        Assert.Equal(HttpStatusCode.NotFound, unknownWithoutOwner.StatusCode);
    }

    [Fact]
    public async Task PrivateWrites_CheckOwnerThenCsrf_BeforeExecutingBookOrLogoutOperations()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        using var anonymousChange = await PostAsync(client, "/api/auth/change-password", null, null);
        Assert.Equal(HttpStatusCode.Unauthorized, anonymousChange.StatusCode);
        using (var anonymousProblem = JsonDocument.Parse(await anonymousChange.Content.ReadAsStringAsync()))
        {
            Assert.Equal("AuthenticationRequired", anonymousProblem.RootElement.GetProperty("code").GetString());
        }
        var user = await fixture.CreateUserAsync();
        using var login = await RealCookieAccountFixture.LoginAsync(client, user.Email, user.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        using var wrongOwner = await PostAsync(client, "/api/books", "another-user", session.CsrfToken);
        Assert.Equal(HttpStatusCode.Conflict, wrongOwner.StatusCode);
        using var noCsrf = await PostAsync(client, "/api/books", user.Id, null);
        Assert.Equal(HttpStatusCode.BadRequest, noCsrf.StatusCode);
        using (var csrfProblem = JsonDocument.Parse(await noCsrf.Content.ReadAsStringAsync()))
        {
            Assert.Equal("CsrfInvalid", csrfProblem.RootElement.GetProperty("code").GetString());
        }
        using var wrongCsrf = await PostAsync(client, "/api/books", user.Id, "not-a-token");
        Assert.Equal(HttpStatusCode.BadRequest, wrongCsrf.StatusCode);
        client.DefaultRequestHeaders.Add("X-Expected-User", user.Id);
        using var empty = await client.GetAsync("/api/books");
        using (var books = JsonDocument.Parse(await empty.Content.ReadAsStringAsync()))
        {
            Assert.Equal(0, books.RootElement.GetProperty("books").GetArrayLength());
        }
        client.DefaultRequestHeaders.Remove("X-Expected-User");
        using var created = await PostAsync(client, "/api/books", user.Id, session.CsrfToken);
        Assert.Equal(HttpStatusCode.Created, created.StatusCode);
        using var logoutWithoutOwner = await PostAsync(client, "/api/auth/logout", null, session.CsrfToken);
        Assert.Equal(HttpStatusCode.Conflict, logoutWithoutOwner.StatusCode);
        Assert.Equal(user.Id, (await RealCookieAccountFixture.ReadSessionAsync(client)).User?.Id);
        using var logout = await PostAsync(client, "/api/auth/logout", user.Id, session.CsrfToken);
        Assert.Equal(HttpStatusCode.OK, logout.StatusCode);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
    }

    [Fact]
    public async Task AccountJsonMutations_EnforceMediaTypeAndSixteenKiBLimitBeforeCsrfOrBinding()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();

        using var unsupported = new HttpRequestMessage(HttpMethod.Post, "/api/auth/login")
        {
            Content = new StringContent("{}", System.Text.Encoding.UTF8, "text/plain")
        };
        using var unsupportedResponse = await client.SendAsync(unsupported);
        Assert.Equal(HttpStatusCode.UnsupportedMediaType, unsupportedResponse.StatusCode);
        var unsupportedBody = await unsupportedResponse.Content.ReadAsStringAsync();
        Assert.False(string.IsNullOrWhiteSpace(unsupportedBody), $"Content-Type: {unsupportedResponse.Content.Headers.ContentType}; body length: {unsupportedBody.Length}");
        using (var unsupportedProblem = JsonDocument.Parse(unsupportedBody))
        {
            Assert.Equal("UnsupportedMediaType", unsupportedProblem.RootElement.GetProperty("code").GetString());
        }

        using var exactLimit = new HttpRequestMessage(HttpMethod.Post, "/api/auth/login")
        {
            Content = new ByteArrayContent(new byte[16 * 1024])
        };
        exactLimit.Content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/json");
        using var exactResponse = await client.SendAsync(exactLimit);
        Assert.Equal(HttpStatusCode.BadRequest, exactResponse.StatusCode);
        using (var exactProblem = JsonDocument.Parse(await exactResponse.Content.ReadAsStringAsync()))
        {
            Assert.Equal("Invalid request token", exactProblem.RootElement.GetProperty("title").GetString());
            Assert.Equal("CsrfInvalid", exactProblem.RootElement.GetProperty("code").GetString());
        }

        using var oversized = new HttpRequestMessage(HttpMethod.Post, "/api/auth/login")
        {
            Content = new ByteArrayContent(new byte[(16 * 1024) + 1])
        };
        oversized.Content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/json");
        using var oversizedResponse = await client.SendAsync(oversized);
        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, oversizedResponse.StatusCode);
        Assert.True(oversizedResponse.Headers.CacheControl?.NoStore);
        var oversizedBody = await oversizedResponse.Content.ReadAsStringAsync();
        Assert.DoesNotContain("oversized", oversizedBody, StringComparison.OrdinalIgnoreCase);
        using (var oversizedProblem = JsonDocument.Parse(oversizedBody))
        {
            Assert.Equal("RequestTooLarge", oversizedProblem.RootElement.GetProperty("code").GetString());
        }
    }

    [Trait("FrontendProfile", "BlazorAuto")]
    [Fact]
    public async Task AccountWriteLimit_IsIpPartitionedAndSharedAcrossBlazorAndJsonRoutes()
    {
        await using var fixture = new RealCookieAccountFixture(new Dictionary<string, string?>
        {
            ["Accounts:WriteLimit:PermitLimit"] = "2",
            ["Accounts:WriteLimit:WindowSeconds"] = "300"
        });
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var ip = $"198.51.100.{Random.Shared.Next(1, 255)}";

        using var blazorWrite1 = await PostFormAsync(client, "/Account/Logout", ip);
        using var blazorWrite2 = await PostFormAsync(client, "/Account/Logout", ip);
        Assert.NotEqual(HttpStatusCode.TooManyRequests, blazorWrite1.StatusCode);
        Assert.NotEqual(HttpStatusCode.TooManyRequests, blazorWrite2.StatusCode);

        using var sameIpOversizedApiWrite = await PostOversizedJsonAsync(client, "/api/auth/login", ip);
        Assert.Equal(HttpStatusCode.TooManyRequests, sameIpOversizedApiWrite.StatusCode);

        var otherIp = $"203.0.113.{Random.Shared.Next(1, 255)}";
        using var otherIpApiWrite = await PostJsonAsync(client, "/api/auth/login", otherIp);
        Assert.NotEqual(HttpStatusCode.TooManyRequests, otherIpApiWrite.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, otherIpApiWrite.StatusCode);
    }

    [Fact]
    public async Task AccountWriteLimit_IsIpPartitionedAcrossReactJsonAccountRoutes()
    {
        await using var fixture = new RealCookieAccountFixture(new Dictionary<string, string?>
        {
            ["Accounts:WriteLimit:PermitLimit"] = "2",
            ["Accounts:WriteLimit:WindowSeconds"] = "300"
        });
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var ip = $"198.51.100.{Random.Shared.Next(1, 255)}";

        for (var attempt = 0; attempt < 2; attempt++)
        {
            using var allowed = await PostJsonAsync(client, "/api/auth/login", ip);
            Assert.Equal(HttpStatusCode.BadRequest, allowed.StatusCode);
        }

        using var overLimit = await PostJsonAsync(client, "/api/auth/login", ip);
        Assert.Equal(HttpStatusCode.TooManyRequests, overLimit.StatusCode);

        var otherIp = $"203.0.113.{Random.Shared.Next(1, 255)}";
        using var otherIpWrite = await PostJsonAsync(client, "/api/auth/login", otherIp);
        Assert.Equal(HttpStatusCode.BadRequest, otherIpWrite.StatusCode);
    }

    [Fact]
    public async Task AccountJsonWrites_KeepTheExistingApiWindow()
    {
        await using var fixture = new RealCookieAccountFixture(new Dictionary<string, string?>
        {
            ["Accounts:WriteLimit:PermitLimit"] = "10",
            ["RateLimiting:Api:PermitLimit"] = "2",
            ["RateLimiting:Api:WindowSeconds"] = "300"
        });
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var ip = $"203.0.113.{Random.Shared.Next(1, 255)}";

        for (var i = 0; i < 2; i++)
        {
            using var allowed = await PostJsonAsync(client, "/api/auth/login", ip);
            Assert.Equal(HttpStatusCode.BadRequest, allowed.StatusCode);
        }

        using var overLimit = await PostJsonAsync(client, "/api/auth/login", ip);
        Assert.Equal(HttpStatusCode.TooManyRequests, overLimit.StatusCode);
    }

    [Fact]
    public async Task EnabledAccountWrites_KeepTheExistingGeneralGlobalWindow()
    {
        await using var fixture = new RealCookieAccountFixture(new Dictionary<string, string?>
        {
            ["Accounts:WriteLimit:PermitLimit"] = "10",
            ["RateLimiting:Global:PermitLimit"] = "1",
            ["RateLimiting:Global:WindowSeconds"] = "300",
            ["RateLimiting:Api:PermitLimit"] = "10"
        });
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();
        var ip = $"198.51.100.{Random.Shared.Next(1, 255)}";

        using var allowed = await PostJsonAsync(client, "/api/auth/login", ip);
        Assert.Equal(HttpStatusCode.BadRequest, allowed.StatusCode);
        using var overLimit = await PostJsonAsync(client, "/api/auth/login", ip);
        Assert.Equal(HttpStatusCode.TooManyRequests, overLimit.StatusCode);
    }

    private static async Task<HttpResponseMessage> PostAsync(HttpClient client, string path, string? expected, string? csrf)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = JsonContent.Create(new { title = "Guard fixture" })
        };
        if (expected is not null) request.Headers.Add("X-Expected-User", expected);
        if (csrf is not null) request.Headers.Add("X-CSRF-TOKEN", csrf);
        return await client.SendAsync(request);
    }

    private static async Task<HttpResponseMessage> PostFormAsync(HttpClient client, string path, string forwardedIp)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = new FormUrlEncodedContent([])
        };
        request.Headers.TryAddWithoutValidation("X-Forwarded-For", forwardedIp);
        return await client.SendAsync(request);
    }

    private static async Task<HttpResponseMessage> PostJsonAsync(HttpClient client, string path, string forwardedIp)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = JsonContent.Create(new { email = "rate-limit@example.test", password = "invalid" })
        };
        request.Headers.TryAddWithoutValidation("X-Forwarded-For", forwardedIp);
        return await client.SendAsync(request);
    }

    private static async Task<HttpResponseMessage> PostOversizedJsonAsync(HttpClient client, string path, string forwardedIp)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = new ByteArrayContent(new byte[(16 * 1024) + 1])
        };
        request.Content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/json");
        request.Headers.TryAddWithoutValidation("X-Forwarded-For", forwardedIp);
        return await client.SendAsync(request);
    }
}
