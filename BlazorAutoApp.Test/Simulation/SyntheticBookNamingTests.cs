using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Core.Features.Books.UseCases.Shared;
using BlazorAutoApp.Simulation.Books;
using Xunit;

namespace BlazorAutoApp.Test.Simulation;

public sealed class SyntheticBookNamingTests
{
    [Fact]
    public void GeneratedBookUsesTargetRunIdAndSimulationUrl()
    {
        var book = SyntheticBookNaming.Create("local", "20260530T211500Z-ab12cd34", "smoke", 1);

        Assert.StartsWith("[sim-v2:local:20260530T211500Z-ab12cd34]", book.Title, StringComparison.Ordinal);
        Assert.Equal("Traffic Simulation", book.Author);
        Assert.Equal("https://simulation.invalid/books/local/20260530T211500Z-ab12cd34/0001", book.Url);
    }

    [Fact]
    public void GeneratedBookSatisfiesCoreValidationRules()
    {
        var book = SyntheticBookNaming.Create("localcluster-public", "20260530T211500Z-ab12cd34", "smoke", 9999);

        Assert.True(book.Title.Length <= BookRules.TitleMaxLength);
        Assert.True(book.Author.Length <= BookRules.AuthorMaxLength);
        Assert.True(book.Url.Length <= BookRules.UrlMaxLength);
        Assert.True(BookUrlValidation.IsValidOptionalHttpUrl(book.Url));
    }

    [Fact]
    public void SafeDeleteRequiresPrefixForCurrentTargetAndSimulationUrl()
    {
        var safe = new BookListItemResponse
        {
            Id = 1,
            Title = "[sim-v2:local:run] smoke 0001",
            Url = "https://simulation.invalid/books/local/run/0001"
        };
        var wrongTarget = new BookListItemResponse
        {
            Id = 2,
            Title = "[sim-v2:cloud-public:run] smoke 0001",
            Url = "https://simulation.invalid/books/cloud-public/run/0001"
        };
        var wrongUrl = new BookListItemResponse
        {
            Id = 3,
            Title = "[sim-v2:local:run] smoke 0001",
            Url = "https://example.test/books/local/run/0001"
        };

        Assert.True(SyntheticBookNaming.IsSafeToDelete(safe, "local"));
        Assert.False(SyntheticBookNaming.IsSafeToDelete(wrongTarget, "local"));
        Assert.False(SyntheticBookNaming.IsSafeToDelete(wrongUrl, "local"));
    }

    [Fact]
    public void PublicTargetCleanupAcceptsLegacyEdgeMarkers()
    {
        var legacyCloudBook = new BookListItemResponse
        {
            Id = 1,
            Title = "[sim-v2:cloud-edge:run] smoke 0001",
            Url = "https://simulation.invalid/books/cloud-edge/run/0001"
        };
        var legacyLocalClusterBook = new BookListItemResponse
        {
            Id = 2,
            Title = "[sim-v2:localcluster-edge:run] smoke 0001",
            Url = "https://simulation.invalid/books/localcluster-edge/run/0001"
        };

        Assert.True(SyntheticBookNaming.IsSafeToDelete(legacyCloudBook, "cloud-public"));
        Assert.True(SyntheticBookNaming.IsSafeToDelete(legacyLocalClusterBook, "localcluster-public"));
        Assert.False(SyntheticBookNaming.IsSafeToDelete(legacyCloudBook, "localcluster-public"));
    }
}
