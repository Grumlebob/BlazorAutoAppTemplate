using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

[Collection(TestCollectionNames.StartupIntegration)]
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
    public async Task ProtectedBookApi_AnonymousHtmlRequests_Return401WithoutRedirectOrMutation()
    {
        using var client = fixture.Factory.CreateClient(new Microsoft.AspNetCore.Mvc.Testing.WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false
        });
        var bookCountBefore = await CountBooksAsync(fixture.Factory.Services);
        using var createContent = JsonContent.Create(new CreateBookRequest
        {
            Title = "Anonymous write must be denied",
            Author = "No user",
            Url = "https://example.test/anonymous-write"
        });
        using var updateContent = JsonContent.Create(new UpdateBookRequest
        {
            Id = 424242,
            Title = "Anonymous update must be denied",
            Author = "No user",
            Url = "https://example.test/anonymous-update"
        });
        var requests = new[]
        {
            new HttpRequestMessage(HttpMethod.Get, "/api/books"),
            new HttpRequestMessage(HttpMethod.Get, "/api/books/424242"),
            new HttpRequestMessage(HttpMethod.Post, "/api/books") { Content = createContent },
            new HttpRequestMessage(HttpMethod.Put, "/api/books/424242") { Content = updateContent },
            new HttpRequestMessage(HttpMethod.Delete, "/api/books/424242")
        };

        for (var index = 0; index < requests.Length; index++)
        {
            using var request = requests[index];
            request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("text/html"));
            request.Headers.TryAddWithoutValidation("X-Forwarded-For", $"203.0.113.{20 + index}");

            using var response = await client.SendAsync(request);
            var body = await response.Content.ReadAsStringAsync();

            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
            Assert.Null(response.Headers.Location);
            Assert.NotEqual("text/html", response.Content.Headers.ContentType?.MediaType);
            Assert.DoesNotContain("<html", body, StringComparison.OrdinalIgnoreCase);
        }

        Assert.Equal(bookCountBefore, await CountBooksAsync(fixture.Factory.Services));
    }

    [Fact]
    public async Task TestAuthentication_AddsRolesFromHeader()
    {
        using var client = fixture.Factory.CreateAuthenticatedClient($"roles-{Guid.NewGuid():N}@example.test");

        using var withoutRole = new HttpRequestMessage(HttpMethod.Get, HostingResponseBehaviourFixture.RoleProbePath);
        using var withoutRoleResponse = await client.SendAsync(withoutRole);

        using var withRole = new HttpRequestMessage(HttpMethod.Get, HostingResponseBehaviourFixture.RoleProbePath);
        withRole.Headers.TryAddWithoutValidation(TestAuthenticationHandler.RolesHeader, "User, Admin");
        using var withRoleResponse = await client.SendAsync(withRole);

        Assert.Equal(HttpStatusCode.Forbidden, withoutRoleResponse.StatusCode);
        Assert.Equal(HttpStatusCode.OK, withRoleResponse.StatusCode);
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

    private static async Task<int> CountBooksAsync(IServiceProvider services)
    {
        await using var scope = services.CreateAsyncScope();
        var dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
        await using var db = await dbFactory.CreateDbContextAsync();
        return await db.Books.CountAsync();
    }
}

public sealed class HostingResponseBehaviourFixture : IAsyncLifetime
{
    public const int GlobalPermitLimit = 5;
    public const string RoleProbePath = "/__test/role-probe";

    public WebAppFactory Factory { get; } = new(new WebAppFactoryOptions
    {
        GlobalRateLimitPermitLimit = GlobalPermitLimit,
        UseIdentityCookieChallenge = true,
        InitializeDatabaseRespawner = false,
        ConfigureTestServices = services => services.AddTransient<IStartupFilter, RoleProbeStartupFilter>()
    });

    // Test-only endpoint that reports whether the authenticated user has the Admin role.
    private sealed class RoleProbeStartupFilter : IStartupFilter
    {
        public Action<IApplicationBuilder> Configure(Action<IApplicationBuilder> next) => app =>
        {
            app.Map(RoleProbePath, branch => branch.Run(async context =>
            {
                var result = await context.AuthenticateAsync(TestAuthenticationHandler.SchemeName);
                context.Response.StatusCode = result.Principal?.IsInRole("Admin") == true
                    ? StatusCodes.Status200OK
                    : StatusCodes.Status403Forbidden;
            }));
            next(app);
        };
    }

    public async ValueTask InitializeAsync()
    {
        await Factory.InitializeAsync();
    }

    public async ValueTask DisposeAsync()
    {
        await Factory.DisposeAsync();
    }
}
