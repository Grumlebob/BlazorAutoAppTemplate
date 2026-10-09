using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting;

[Collection(TestCollectionNames.Integration)]
public sealed class AppHeadAssetTests(WebAppFactory factory)
{
    private static readonly byte[] PngSignature = [137, 80, 78, 71, 13, 10, 26, 10];
    private readonly HttpClient _client = factory.HttpClient;

    [Fact]
    public async Task HomePage_DeclaresStandardPngFavicon()
    {
        var href = await GetFaviconHrefAsync();
        Assert.Contains("favicon", href, StringComparison.OrdinalIgnoreCase);
        Assert.EndsWith(".png", href.Split('?', 2)[0], StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task DeclaredFavicon_IsServedAndMatchesCanonicalAsset()
    {
        var href = await GetFaviconHrefAsync();
        var declared = await GetPngAsync(href);
        var canonical = await GetPngAsync("/favicon.png");
        Assert.Equal(canonical, declared);
    }

    private async Task<string> GetFaviconHrefAsync()
    {
        var html = await _client.GetStringAsync("/");
        var icons = Regex.Matches(html, "<link\\s+[^>]*>", RegexOptions.IgnoreCase)
            .Select(match => Regex.Matches(
                    match.Value,
                    "(?<name>[a-zA-Z0-9:-]+)=\"(?<value>[^\"]*)\"",
                    RegexOptions.IgnoreCase)
                .ToDictionary(
                    attribute => attribute.Groups["name"].Value,
                    attribute => WebUtility.HtmlDecode(attribute.Groups["value"].Value),
                    StringComparer.OrdinalIgnoreCase))
            .Where(attributes => attributes.TryGetValue("rel", out var rel)
                && rel.Split(' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                    .Contains("icon", StringComparer.OrdinalIgnoreCase)
                && attributes.TryGetValue("type", out var type)
                && string.Equals(type, "image/png", StringComparison.OrdinalIgnoreCase))
            .ToArray();
        var icon = Assert.Single(icons);
        Assert.True(icon.TryGetValue("href", out var href));
        Assert.False(string.IsNullOrWhiteSpace(href));
        return href!;
    }

    private async Task<byte[]> GetPngAsync(string href)
    {
        using var response = await _client.GetAsync(href);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("image/png", response.Content.Headers.ContentType?.MediaType);
        var bytes = await response.Content.ReadAsByteArrayAsync();
        Assert.True(bytes.Length >= PngSignature.Length, "The favicon must contain a PNG header.");
        Assert.True(bytes.AsSpan(0, PngSignature.Length).SequenceEqual(PngSignature), "The favicon must be a PNG.");
        return bytes;
    }
}
