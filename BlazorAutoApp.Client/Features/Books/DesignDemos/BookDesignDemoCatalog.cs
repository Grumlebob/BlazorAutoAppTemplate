using BlazorAutoApp.Client.Features.Books.Shared;

namespace BlazorAutoApp.Client.Features.Books.DesignDemos;

public static class BookDesignDemoCatalog
{
    public static IReadOnlyList<BookDesignDemo> All { get; } =
        BookCoverDesignCatalog.All.Select(definition => new BookDesignDemo(definition)).ToArray();

    public static BookDesignDemo? Find(string? id) =>
        All.FirstOrDefault(design => string.Equals(design.Id, id, StringComparison.OrdinalIgnoreCase));

    public static BookDesignDemo Previous(BookDesignDemo design)
    {
        var index = IndexOf(design);
        return All[(index + All.Count - 1) % All.Count];
    }

    public static BookDesignDemo Next(BookDesignDemo design)
    {
        var index = IndexOf(design);
        return All[(index + 1) % All.Count];
    }

    public static string DetailsUrl(BookDesignDemo design, bool forcedOpen = false) =>
        $"/books/design-demos/{design.Id}{(forcedOpen ? "?open=true" : string.Empty)}";

    public static int IndexOf(BookDesignDemo design)
    {
        for (var index = 0; index < All.Count; index++)
        {
            if (All[index] == design)
            {
                return index;
            }
        }

        return 0;
    }
}

public sealed record BookDesignDemo(BookCoverDesignDefinition Definition)
{
    public string Id => Definition.Id;

    public string Label => Definition.Label;

    public IReadOnlyList<string> TitleLines => Definition.DemoTitleLines;

    public int TitleY => Definition.DemoTitleY;

    public string TitleDy => Definition.DemoTitleDy;

    public string TitleFontSize => Definition.DemoTitleFontSize;

    public string TitleFill => Definition.DemoTitleFill;

    public string Note => Definition.Note;

    public BookCoverDesignColors CoverColors => Definition.CoverColors;

    public BookCoverDesignColors PageColors => Definition.PageColors;

    public string CoverPath => Definition.CoverPath;

    public string PagePath => Definition.PagePath;

    public string LineStroke => Definition.LineStroke;

    public BookCoverTitlePlate Plate => Definition.Plate;

    public BookCoverDesignKind Kind => Definition.Kind;
}
