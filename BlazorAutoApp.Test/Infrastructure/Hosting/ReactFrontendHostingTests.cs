using System.Net;
using System.Net.Http.Headers;
using System.Text;
using BlazorAutoApp.Frontend;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

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

        using var get = CreateHtmlRequest(HttpMethod.Get, "/books/author/example");
        using var getResponse = await host.Client.SendAsync(get);

        Assert.Equal(HttpStatusCode.OK, getResponse.StatusCode);
        Assert.Equal("text/html", getResponse.Content.Headers.ContentType?.MediaType);
        Assert.Equal(ReactTestHost.Shell, await getResponse.Content.ReadAsStringAsync());

        using var head = CreateHtmlRequest(HttpMethod.Head, "/books");
        using var headResponse = await host.Client.SendAsync(head);

        Assert.Equal(HttpStatusCode.OK, headResponse.StatusCode);
        Assert.Equal((long)ReactTestHost.Shell.Length, headResponse.Content.Headers.ContentLength);
        Assert.Empty(await headResponse.Content.ReadAsByteArrayAsync());
    }

    [Fact]
    public async Task StaticAssets_AreServedAndMissingAssetsRemain404()
    {
        await using var host = await ReactTestHost.CreateAsync();

        using var assetResponse = await host.Client.GetAsync("/assets/app.js");

        Assert.Equal(HttpStatusCode.OK, assetResponse.StatusCode);
        Assert.Equal("export {};", await assetResponse.Content.ReadAsStringAsync());

        using var missingResponse = await host.Client.GetAsync("/assets/missing.js");

        Assert.Equal(HttpStatusCode.NotFound, missingResponse.StatusCode);
        Assert.DoesNotContain("<html", await missingResponse.Content.ReadAsStringAsync(), StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData("/Account")]
    [InlineData("/account/profile")]
    [InlineData("/API/auth")]
    [InlineData("/api/unknown")]
    [InlineData("/signin-google")]
    [InlineData("/SIGNIN-OIDC/callback")]
    [InlineData("/oauth/callback")]
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

    private sealed class ReactTestHost : IAsyncDisposable
    {
        public const string Shell = "<!doctype html><title>React test shell</title>";
        public const string Secret = "outside-root-secret";

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

        public static async Task<ReactTestHost> CreateAsync()
        {
            var rootPath = Directory.CreateTempSubdirectory("react-static-root-").FullName;
            var assetPath = Path.Combine(rootPath, "assets");
            Directory.CreateDirectory(assetPath);
            await File.WriteAllTextAsync(Path.Combine(rootPath, "index.html"), Shell);
            await File.WriteAllTextAsync(Path.Combine(assetPath, "app.js"), "export {};");

            var outsideSecretPath = Path.Combine(Path.GetDirectoryName(rootPath)!, $"{Path.GetFileName(rootPath)}-secret.txt");
            await File.WriteAllTextAsync(outsideSecretPath, Secret);

            var builder = WebApplication.CreateBuilder(new WebApplicationOptions
            {
                EnvironmentName = Environments.Development
            });
            builder.WebHost.UseTestServer();
            var app = builder.Build();
            var fileProvider = new PhysicalFileProvider(rootPath);
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
