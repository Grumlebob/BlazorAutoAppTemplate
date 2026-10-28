using System.Net;
using System.Net.Http.Headers;
using System.IO.Compression;
using System.Text;
using System.Text.RegularExpressions;
using GrumPlates.Features.Accounts.Identity;
using GrumPlates.Frontend;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Xunit;

namespace GrumPlates.Test.Infrastructure.Hosting;

public sealed class ReactFrontendHostingTests
{
    [Fact]
    public async Task HtmlNavigation_UsesShellForGetAndHead()
    {
        await using var host = await ReactTestHost.CreateAsync();

        using var rootRequest = CreateHtmlRequest(HttpMethod.Get, "/");
        using var rootResponse = await host.Client.SendAsync(rootRequest);

        Assert.Equal(HttpStatusCode.OK, rootResponse.StatusCode);
        Assert.Equal(ReactTestHost.Shell, await rootResponse.Content.ReadAsStringAsync());
        Assert.True(rootResponse.Headers.CacheControl?.NoCache);

        using var get = CreateHtmlRequest(HttpMethod.Get, "/books/author/example");
        using var getResponse = await host.Client.SendAsync(get);

        Assert.Equal(HttpStatusCode.OK, getResponse.StatusCode);
        Assert.Equal("text/html", getResponse.Content.Headers.ContentType?.MediaType);
        Assert.Equal(ReactTestHost.SpaFallback, await getResponse.Content.ReadAsStringAsync());

        using var head = CreateHtmlRequest(HttpMethod.Head, "/books");
        using var headResponse = await host.Client.SendAsync(head);

        Assert.Equal(HttpStatusCode.OK, headResponse.StatusCode);
        Assert.Equal((long)ReactTestHost.SpaFallback.Length, headResponse.Content.Headers.ContentLength);
        Assert.Empty(await headResponse.Content.ReadAsByteArrayAsync());
    }

    [Fact]
    public async Task StaticAssets_AreServedAndMissingAssetsRemain404()
    {
        await using var host = await ReactTestHost.CreateAsync();

        using var assetResponse = await host.Client.GetAsync("/assets/app.js");

        Assert.Equal(HttpStatusCode.OK, assetResponse.StatusCode);
        Assert.Equal("export {};", await assetResponse.Content.ReadAsStringAsync());
        Assert.True(assetResponse.Headers.CacheControl?.NoCache);

        using var fingerprintedResponse = await host.Client.GetAsync("/assets/app-a1b2c3d4.js");
        Assert.Equal(HttpStatusCode.OK, fingerprintedResponse.StatusCode);
        var fingerprintedCache = fingerprintedResponse.Headers.CacheControl;
        Assert.NotNull(fingerprintedCache);
        Assert.True(fingerprintedCache!.Public);
        Assert.Equal(TimeSpan.FromDays(365), fingerprintedCache.MaxAge);
        Assert.Contains("immutable", fingerprintedCache.ToString(), StringComparison.OrdinalIgnoreCase);

        using var missingResponse = await host.Client.GetAsync("/assets/missing.js");

        Assert.Equal(HttpStatusCode.NotFound, missingResponse.StatusCode);
        Assert.DoesNotContain("<html", await missingResponse.Content.ReadAsStringAsync(), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task StaticAssets_AreGzipCompressedWhenRequested()
    {
        await using var host = await ReactTestHost.CreateAsync(forceHttps: true);

        foreach (var (path, content) in new[] { ("/assets/app.css", ReactTestHost.Stylesheet), ("/assets/mark.svg", ReactTestHost.Mark) })
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, path);
            request.Headers.AcceptEncoding.Add(new StringWithQualityHeaderValue("gzip"));
            using var response = await host.Client.SendAsync(request);

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Contains("gzip", response.Content.Headers.ContentEncoding);
            var compressed = await response.Content.ReadAsByteArrayAsync();
            Assert.True(compressed.Length < Encoding.UTF8.GetByteCount(content));

            await using var source = new MemoryStream(compressed);
            await using var gzip = new GZipStream(source, CompressionMode.Decompress);
            using var reader = new StreamReader(gzip, Encoding.UTF8);
            Assert.Equal(content, await reader.ReadToEndAsync());
        }
    }

    [Fact]
    public async Task ReactResponses_UseRestrictiveSecurityHeaders()
    {
        await using var host = await ReactTestHost.CreateAsync();

        using var shellRequest = CreateHtmlRequest(HttpMethod.Get, "/books");
        using var shellResponse = await host.Client.SendAsync(shellRequest);
        AssertSecurityHeaders(shellResponse);

        using var assetResponse = await host.Client.GetAsync("/assets/app.js");
        AssertSecurityHeaders(assetResponse);

        using var reservedRequest = CreateHtmlRequest(HttpMethod.Get, "/api/auth/login");
        using var reservedResponse = await host.Client.SendAsync(reservedRequest);
        Assert.Equal(HttpStatusCode.NotFound, reservedResponse.StatusCode);
        AssertSecurityHeaders(reservedResponse);

        using var privateApiResponse = await host.Client.GetAsync("/api/books");
        Assert.Equal(HttpStatusCode.NotFound, privateApiResponse.StatusCode);
        Assert.True(privateApiResponse.Headers.CacheControl?.Private);
        Assert.True(privateApiResponse.Headers.CacheControl?.NoStore);
    }

    [Fact]
    public async Task InlineNavigationScripts_AreAllowedByExactHashes()
    {
        const string shell = "<!doctype html><script>window.reactBooted = true;</script>";
        const string spaFallback = "<!doctype html><script>window.reactFallback = true;</script>";
        await using var host = await ReactTestHost.CreateAsync(shell: shell, spaFallback: spaFallback);
        using var request = CreateHtmlRequest(HttpMethod.Get, "/books");

        using var response = await host.Client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var policy = Assert.Single(response.Headers.GetValues("Content-Security-Policy"));
        var shellHash = Convert.ToBase64String(System.Security.Cryptography.SHA256.HashData(Encoding.UTF8.GetBytes("window.reactBooted = true;")));
        var fallbackHash = Convert.ToBase64String(System.Security.Cryptography.SHA256.HashData(Encoding.UTF8.GetBytes("window.reactFallback = true;")));
        Assert.Contains($"'sha256-{shellHash}'", policy, StringComparison.Ordinal);
        Assert.Contains($"'sha256-{fallbackHash}'", policy, StringComparison.Ordinal);
        Assert.DoesNotContain("unsafe-inline", policy, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("unsafe-eval", policy, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task HtmlDocuments_CarryAFreshScriptNonceForEdgeInjectedScripts()
    {
        await using var host = await ReactTestHost.CreateAsync();

        using var firstRequest = CreateHtmlRequest(HttpMethod.Get, "/");
        using var first = await host.Client.SendAsync(firstRequest);
        using var secondRequest = CreateHtmlRequest(HttpMethod.Get, "/");
        using var second = await host.Client.SendAsync(secondRequest);
        using var asset = await host.Client.GetAsync("/assets/app.js");
        using var apiResponse = await host.Client.GetAsync("/api/books");

        var nonces = new[] { first, second }
            .Select(response =>
            {
                var policy = Assert.Single(response.Headers.GetValues("Content-Security-Policy"));
                var match = Regex.Match(policy, "script-src 'self' 'nonce-(?<nonce>[A-Za-z0-9+/]{22}==)'");
                Assert.True(match.Success, "A document CSP must carry a 128-bit script nonce.");
                Assert.DoesNotContain("unsafe-inline", policy, StringComparison.OrdinalIgnoreCase);
                return match.Groups["nonce"].Value;
            })
            .ToArray();

        Assert.NotEqual(nonces[0], nonces[1]);
        Assert.DoesNotContain(nonces[0], await first.Content.ReadAsStringAsync(), StringComparison.Ordinal);
        foreach (var response in new[] { asset, apiResponse })
        {
            var policy = Assert.Single(response.Headers.GetValues("Content-Security-Policy"));
            Assert.DoesNotContain("'nonce-", policy, StringComparison.Ordinal);
            Assert.DoesNotContain("unsafe-inline", policy, StringComparison.OrdinalIgnoreCase);
        }
    }

    [Fact]
    public async Task SelectedProductionMiddleware_AddsHstsForHttpsRequests()
    {
        await using var host = await ReactTestHost.CreateAsync(
            environmentName: Environments.Production,
            useSelectedFrontendMiddleware: true,
            forceHttps: true);
        using var request = CreateHtmlRequest(HttpMethod.Get, "https://example.test/books");

        using var response = await host.Client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var hsts = Assert.Single(response.Headers.GetValues("Strict-Transport-Security"));
        Assert.Contains("max-age=", hsts, StringComparison.OrdinalIgnoreCase);
        if (IsReactCompositionSelected())
        {
            AssertSecurityHeaders(response);
        }
    }

    [Theory]
    [InlineData("/Account")]
    [InlineData("/Account/Login")]
    [InlineData("/ACCOUNT/Register")]
    [InlineData("/account/profile")]
    [InlineData("/API/auth")]
    [InlineData("/api/auth/login")]
    [InlineData("/API/AUTH/google")]
    [InlineData("/api/unknown")]
    [InlineData("/signin-google")]
    [InlineData("/signin-oidc")]
    [InlineData("/SIGNIN-OIDC/callback")]
    [InlineData("/oauth/callback")]
    [InlineData("/OAuth2/Callback")]
    [InlineData("/health/ready")]
    [InlineData("/_framework/missing")]
    [InlineData("/_content/missing")]
    public async Task ReservedPaths_Return404InsteadOfShell(string path)
    {
        await using var host = await ReactTestHost.CreateAsync();
        using var request = CreateHtmlRequest(HttpMethod.Get, path);

        using var response = await host.Client.SendAsync(request);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.DoesNotContain("<html", await response.Content.ReadAsStringAsync(), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task NonHtmlAndUnsafeRequests_DoNotReceiveShell()
    {
        await using var host = await ReactTestHost.CreateAsync();
        using var jsonRequest = new HttpRequestMessage(HttpMethod.Get, "/books");
        jsonRequest.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

        using var jsonResponse = await host.Client.SendAsync(jsonRequest);

        Assert.Equal(HttpStatusCode.NotFound, jsonResponse.StatusCode);

        using var postRequest = CreateHtmlRequest(HttpMethod.Post, "/books");
        postRequest.Content = new StringContent("unsafe", Encoding.UTF8, "text/plain");
        using var postResponse = await host.Client.SendAsync(postRequest);

        Assert.Equal(HttpStatusCode.NotFound, postResponse.StatusCode);
        Assert.DoesNotContain("<html", await postResponse.Content.ReadAsStringAsync(), StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData("text/html;q=0")]
    [InlineData("text/html;q=invalid")]
    [InlineData("text/html;q=1;q=0")]
    public async Task ZeroOrInvalidHtmlQuality_DoesNotReceiveShell(string acceptHeader)
    {
        await using var host = await ReactTestHost.CreateAsync();
        using var request = new HttpRequestMessage(HttpMethod.Get, "/books");
        request.Headers.TryAddWithoutValidation("Accept", acceptHeader);

        using var response = await host.Client.SendAsync(request);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.DoesNotContain("<html", await response.Content.ReadAsStringAsync(), StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task TraversalRequest_CannotReadOutsideSelectedRoot()
    {
        await using var host = await ReactTestHost.CreateAsync();
        var traversalPaths = new[]
        {
            "/%2e%2e/secret.txt",
            "/assets/%2e%2e/%2e%2e/secret.txt"
        };

        foreach (var path in traversalPaths)
        {
            using var response = await host.Client.GetAsync(path);

            Assert.False(response.IsSuccessStatusCode, $"Traversal path '{path}' must not be served.");
            Assert.DoesNotContain(ReactTestHost.Secret, await response.Content.ReadAsStringAsync(), StringComparison.Ordinal);
        }
    }

    private static HttpRequestMessage CreateHtmlRequest(HttpMethod method, string path)
    {
        var request = new HttpRequestMessage(method, path);
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("text/html"));
        return request;
    }

    private static void AssertSecurityHeaders(HttpResponseMessage response)
    {
        Assert.Equal("nosniff", Assert.Single(response.Headers.GetValues("X-Content-Type-Options")));
        Assert.Equal("DENY", Assert.Single(response.Headers.GetValues("X-Frame-Options")));
        Assert.Equal(
            "strict-origin-when-cross-origin",
            Assert.Single(response.Headers.GetValues("Referrer-Policy")));
        Assert.Equal(ReactFrontendHosting.PermissionsPolicy, Assert.Single(response.Headers.GetValues("Permissions-Policy")));
        Assert.Equal(
            ReactFrontendHosting.CrossOriginOpenerPolicy,
            Assert.Single(response.Headers.GetValues("Cross-Origin-Opener-Policy")));
        Assert.Equal(
            ReactFrontendHosting.CrossOriginResourcePolicy,
            Assert.Single(response.Headers.GetValues("Cross-Origin-Resource-Policy")));

        // HTML documents add a per-response script nonce to the base policy; every other response keeps it as is.
        var policy = Assert.Single(response.Headers.GetValues("Content-Security-Policy"));
        var isHtml = response.Content.Headers.ContentType?.MediaType == "text/html";
        Assert.Equal(isHtml, Regex.IsMatch(policy, "'nonce-[A-Za-z0-9+/]{22}=='"));
        var basePolicy = Regex.Replace(policy, " 'nonce-[A-Za-z0-9+/]{22}=='", string.Empty);
        Assert.Equal(ReactFrontendHosting.ContentSecurityPolicy, basePolicy);
        Assert.DoesNotContain("unsafe-inline", policy, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("unsafe-eval", policy, StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsReactCompositionSelected()
    {
        var services = new ServiceCollection();
        FrontendComposition.AddFrontendServices(services, new ConfigurationBuilder().Build());
        var currentUser = Assert.Single(services, descriptor => descriptor.ServiceType == typeof(ICurrentUserAccessor));
        return currentUser.ImplementationType == typeof(HttpPrincipalCurrentUserAccessor);
    }

    private sealed class ReactTestHost : IAsyncDisposable
    {
        public const string Shell = "<!doctype html><title>React test shell</title>";
        public const string SpaFallback = "<!doctype html><title>React SPA fallback</title>";
        public const string Secret = "outside-root-secret";
        public static readonly string Stylesheet = string.Concat(
            Enumerable.Repeat(".catalog-card { color: #123456; background: white; }\n", 128));
        public static readonly string Mark = "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 64 64\">"
            + string.Concat(Enumerable.Repeat("<path d=\"M8 8h48v48H8z\" fill=\"#123456\"/>", 32))
            + "</svg>";

        private readonly string _rootPath;
        private readonly string _outsideSecretPath;
        private readonly PhysicalFileProvider _fileProvider;

        private ReactTestHost(WebApplication app, HttpClient client, string rootPath, string outsideSecretPath, PhysicalFileProvider fileProvider)
        {
            App = app;
            Client = client;
            _rootPath = rootPath;
            _outsideSecretPath = outsideSecretPath;
            _fileProvider = fileProvider;
        }

        public WebApplication App { get; }

        public HttpClient Client { get; }

        public static async Task<ReactTestHost> CreateAsync(
            string environmentName = "Development",
            bool useSelectedFrontendMiddleware = false,
            bool forceHttps = false,
            string? shell = null,
            string? spaFallback = null)
        {
            var rootPath = Directory.CreateTempSubdirectory("react-static-root-").FullName;
            var assetPath = Path.Combine(rootPath, "assets");
            Directory.CreateDirectory(assetPath);
            await File.WriteAllTextAsync(Path.Combine(rootPath, "index.html"), shell ?? Shell);
            await File.WriteAllTextAsync(Path.Combine(rootPath, "__spa-fallback.html"), spaFallback ?? SpaFallback);
            await File.WriteAllTextAsync(Path.Combine(assetPath, "app.js"), "export {};");
            await File.WriteAllTextAsync(Path.Combine(assetPath, "app-a1b2c3d4.js"), "export {}; ");
            await File.WriteAllTextAsync(Path.Combine(assetPath, "app.css"), Stylesheet);
            await File.WriteAllTextAsync(Path.Combine(assetPath, "mark.svg"), Mark);

            var outsideSecretPath = Path.Combine(Path.GetDirectoryName(rootPath)!, $"{Path.GetFileName(rootPath)}-secret.txt");
            await File.WriteAllTextAsync(outsideSecretPath, Secret);

            var builder = WebApplication.CreateBuilder(new WebApplicationOptions
            {
                EnvironmentName = environmentName
            });
            builder.Services.AddProblemDetails();
            ReactFrontendHosting.AddResponseCompression(builder.Services);
            builder.WebHost.UseTestServer();
            var app = builder.Build();
            var fileProvider = new PhysicalFileProvider(rootPath);
            if (forceHttps)
            {
                app.Use(async (context, next) =>
                {
                    context.Request.Scheme = "https";
                    await next();
                });
            }

            if (useSelectedFrontendMiddleware)
            {
                FrontendComposition.UseFrontendMiddleware(app);
            }
            else
            {
                ReactFrontendHosting.UseSecurityHeaders(app, fileProvider);
            }

            ReactFrontendHosting.UseStaticFiles(app, fileProvider);
            ReactFrontendHosting.MapNavigationFallback(app, fileProvider);
            await app.StartAsync();

            return new ReactTestHost(app, app.GetTestClient(), rootPath, outsideSecretPath, fileProvider);
        }

        public async ValueTask DisposeAsync()
        {
            Client.Dispose();
            await App.DisposeAsync();
            _fileProvider.Dispose();
            Directory.Delete(_rootPath, recursive: true);
            File.Delete(_outsideSecretPath);
        }
    }
}
