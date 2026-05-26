namespace BlazorAutoApp.Client.Features.Books.DesignDemos;

public static class BookDesignDemoCatalog
{
    public static IReadOnlyList<BookDesignDemo> All { get; } =
    [
        new(
            Id: "cloth-hardback",
            Label: "Cloth Hardback",
            TitleLines: ["The Great", "Gatsby"],
            TitleY: 99,
            TitleDy: "1.28em",
            TitleFontSize: "11.5",
            TitleFill: "#111827",
            Note: "Closest to the hardback direction. No dark spine strip, a larger title plate, restrained page motion, and clear right-side page gutter.",
            CoverColors: new("#2f6f82", "#1f4e5f", "#123342"),
            PageColors: new("#fff9ed", "#f1e3cf", "#d6c8b8"),
            CoverPath: "M27 18h84c14 0 25 12 25 27v126c0 15-11 27-25 27H27c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M108 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#a99f91",
            Plate: new(26, 62, 94, 88, 11, 32, 68, 82, 76, 8, 73, "#f8fafc", "#e0f2fe"),
            Artwork: BookDesignArtwork.ClothHardback),
        new(
            Id: "modern-paperback",
            Label: "Modern Paperback",
            TitleLines: ["Ship"],
            TitleY: 113,
            TitleDy: "1.18em",
            TitleFontSize: "11",
            TitleFill: "#1c1917",
            Note: "Trade-paperback blocking with the same squared page-left edge and quiet central title field.",
            CoverColors: new("#f59e0b", "#9a3412", "#431407"),
            PageColors: new("#fff7ed", "#f0dfc7", "#d7cabc"),
            CoverPath: "M26 20h85c14 0 25 12 25 27v124c0 15-11 27-25 27H26c-12 0-22-10-22-22V42c0-12 10-22 22-22z",
            PagePath: "M109 26h24c16 0 28 12 28 28v114c0 18-12 31-31 31h-21z",
            LineStroke: "#a99f91",
            Plate: new(35, 76, 86, 66, 9, 41, 82, 74, 54, 7, 78, "#fff7ed", "#fed7aa"),
            Artwork: BookDesignArtwork.ModernPaperback),
        new(
            Id: "technical-manual",
            Label: "Technical Manual",
            TitleLines: ["Improved", "Db"],
            TitleY: 106,
            TitleDy: "1.18em",
            TitleFontSize: "11",
            TitleFill: "#1f2937",
            Note: "Manual/reference style without a heavy dark side block. Side tabs sit on the page block, not the cover.",
            CoverColors: new("#4d7c0f", "#365314", "#1a2e05"),
            PageColors: new("#fefce8", "#eee8c9", "#d6d3d1"),
            CoverPath: "M26 18h85c14 0 25 12 25 27v126c0 15-11 27-25 27H26c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M109 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#9b958c",
            Plate: new(35, 77, 86, 66, 7, 41, 83, 74, 54, 5, 78, "#f7fee7", "#d9f99d"),
            Artwork: BookDesignArtwork.TechnicalManual),
        new(
            Id: "decorative-hardcover",
            Label: "Decorative Hardcover",
            TitleLines: ["Trace", "Back"],
            TitleY: 103,
            TitleDy: "1.2em",
            TitleFontSize: "11.5",
            TitleFill: "#111827",
            Note: "Decorative hardcover with ornament outside the protected title plate.",
            CoverColors: new("#4338ca", "#581c87", "#2e1065"),
            PageColors: new("#fff7ed", "#f1e7d7", "#d6d3d1"),
            CoverPath: "M26 18h85c14 0 25 12 25 27v126c0 15-11 27-25 27H26c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M109 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#a99f91",
            Plate: new(35, 76, 86, 68, 10, 41, 82, 74, 56, 7, 78, "#eef2ff", "#c7d2fe"),
            Artwork: BookDesignArtwork.DecorativeHardcover),
        new(
            Id: "library-ledger",
            Label: "Library Ledger",
            TitleLines: ["Kino", "Join"],
            TitleY: 106,
            TitleDy: "1.18em",
            TitleFontSize: "11",
            TitleFill: "#111827",
            Note: "Formal ledger design with the centered plate and clear lower page detail.",
            CoverColors: new("#be123c", "#9f1239", "#4c0519"),
            PageColors: new("#fefce8", "#eee8c9", "#cfc7b8"),
            CoverPath: "M26 18h85c14 0 25 12 25 27v126c0 15-11 27-25 27H26c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M109 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#9b958c",
            Plate: new(35, 76, 86, 68, 8, 41, 82, 74, 56, 6, 78, "#fff1f2", "#fecdd3"),
            Artwork: BookDesignArtwork.LibraryLedger),
        new(
            Id: "field-notebook",
            Label: "Field Notebook",
            TitleLines: ["Designing", "Reliable", "Systems"],
            TitleY: 95,
            TitleDy: "1.18em",
            TitleFontSize: "11",
            TitleFill: "#111827",
            Note: "Notebook-inspired design with right-side page hints and no dark right-side block.",
            CoverColors: new("#0f766e", "#0f766e", "#134e4a"),
            PageColors: new("#fff9ed", "#f4ead9", "#d8d0c4"),
            CoverPath: "M27 18h84c14 0 25 12 25 27v126c0 15-11 27-25 27H27c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M109 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#a8a29e",
            Plate: new(34, 74, 88, 72, 10, 40, 80, 76, 60, 7, 78, "#f0fdfa", "#ccfbf1"),
            Artwork: BookDesignArtwork.FieldNotebook)
    ];

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

public sealed record BookDesignDemo(
    string Id,
    string Label,
    IReadOnlyList<string> TitleLines,
    int TitleY,
    string TitleDy,
    string TitleFontSize,
    string TitleFill,
    string Note,
    BookDesignColors CoverColors,
    BookDesignColors PageColors,
    string CoverPath,
    string PagePath,
    string LineStroke,
    BookDesignTitlePlate Plate,
    BookDesignArtwork Artwork);

public sealed record BookDesignColors(string Start, string Middle, string End);

public sealed record BookDesignTitlePlate(
    int X,
    int Y,
    int Width,
    int Height,
    int Radius,
    int InnerX,
    int InnerY,
    int InnerWidth,
    int InnerHeight,
    int InnerRadius,
    int TextX,
    string Fill,
    string Stroke);

public enum BookDesignArtwork
{
    ClothHardback,
    ModernPaperback,
    TechnicalManual,
    DecorativeHardcover,
    LibraryLedger,
    FieldNotebook
}
