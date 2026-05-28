using BlazorAutoApp.Client.Features.Books.Shared;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Client;

public sealed class BookCoverGeometryTests
{
    [Fact]
    public void Catalog_CoversEveryDesignKind()
    {
        var kinds = BookCoverDesignCatalog.All.Select(design => design.Kind).ToArray();

        Assert.Equal(Enum.GetValues<BookCoverDesignKind>().Length, kinds.Length);
        Assert.Equal(kinds.Length, kinds.Distinct().Count());
    }

    [Fact]
    public void Catalog_UsesUniqueDesignIds()
    {
        var ids = BookCoverDesignCatalog.All.Select(design => design.Id).ToArray();

        Assert.Equal(ids.Length, ids.Distinct(StringComparer.OrdinalIgnoreCase).Count());
    }

    [Fact]
    public void Catalog_DoesNotExposePerDesignShellPaths()
    {
        var propertyNames = typeof(BookCoverDesignDefinition)
            .GetProperties()
            .Select(property => property.Name)
            .ToArray();

        Assert.DoesNotContain("CoverPath", propertyNames);
        Assert.DoesNotContain("PagePath", propertyNames);
    }

    [Fact]
    public void Catalog_CentersEveryTitlePlateOnSharedTitleCenter()
    {
        foreach (var design in BookCoverDesignCatalog.All)
        {
            var plate = design.Plate;

            Assert.Equal(BookCoverGeometry.TitleCenterX, plate.TextX);
            Assert.Equal(BookCoverGeometry.TitleCenterX * 2, (plate.X * 2) + plate.Width);
            Assert.Equal(BookCoverGeometry.TitleCenterX * 2, (plate.InnerX * 2) + plate.InnerWidth);
        }
    }

    [Fact]
    public void Catalog_KeepsEveryTitlePlateInsideCoverSafeArea()
    {
        foreach (var design in BookCoverDesignCatalog.All)
        {
            var plate = design.Plate;

            Assert.True(plate.X >= BookCoverGeometry.CoverSafeLeft, $"{design.Label} starts before the cover safe area.");
            Assert.True(plate.X + plate.Width <= BookCoverGeometry.CoverSafeRight, $"{design.Label} extends beyond the cover safe area.");
        }
    }
}
