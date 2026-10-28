using GrumPlates.Test.TestSupport.Integration;

namespace GrumPlates.Test.Infrastructure.Hosting;

[Collection(TestCollectionNames.Integration)]
[Trait("FrontendProfile", "BlazorAuto")]
public sealed class RenderModeHtmlTests(WebAppFactory factory)
{
    private readonly HttpClient _client = factory.HttpClient;

    [Theory]
    [InlineData("/Account/Register")]
    [InlineData("/Account/ForgotPassword")]
    [InlineData("/Account/Login")]
    public async Task StaticAndAccountPages_DoNotLoadInteractiveBlazorRuntime(string path)
    {
        var html = await _client.GetStringAsync(path);

        Assert.DoesNotContain("src=\"_framework/blazor.web", html, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("\"type\":\"auto\"", html, StringComparison.Ordinal);
    }

    [Fact]
    public async Task HomePage_StillLoadsInteractiveAutoRuntime()
    {
        var html = await _client.GetStringAsync("/");

        Assert.Contains("src=\"_framework/blazor.web", html, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("Blazor-WebAssembly", html, StringComparison.Ordinal);
        Assert.Contains("\"type\":\"auto\"", html, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("/")]
    [InlineData("/books")]
    public async Task PublicPages_DoNotReferenceRemovedScopedCssBundle(string path)
    {
        var html = await _client.GetStringAsync(path);

        Assert.DoesNotContain("GrumPlates.styles.css", html, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("bundle.scp.css", html, StringComparison.OrdinalIgnoreCase);
    }
}
