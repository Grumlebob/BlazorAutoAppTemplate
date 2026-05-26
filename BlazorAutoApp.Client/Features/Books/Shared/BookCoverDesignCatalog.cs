namespace BlazorAutoApp.Client.Features.Books.Shared;

public static class BookCoverDesignCatalog
{
    public static IReadOnlyList<BookCoverDesignDefinition> All { get; } =
    [
        new(
            Kind: BookCoverDesignKind.ClothHardback,
            Id: "cloth-hardback",
            Label: "Cloth Hardback",
            DemoTitleLines: ["The Great", "Gatsby"],
            DemoTitleY: 99,
            DemoTitleDy: "1.28em",
            DemoTitleFontSize: "11.5",
            DemoTitleFill: "#111827",
            Note: "Clean cloth hardback with a centered title plate, restrained page motion, and a quiet right-side page gutter.",
            CoverColors: new("#2f6f82", "#1f4e5f", "#123342"),
            PageColors: new("#fff9ed", "#f1e3cf", "#d6c8b8"),
            CoverPath: "M27 18h84c14 0 25 12 25 27v126c0 15-11 27-25 27H27c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M108 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#a99f91",
            Plate: new(26, 62, 94, 88, 11, 32, 68, 82, 76, 8, 73, "#f8fafc", "#e0f2fe")),
        new(
            Kind: BookCoverDesignKind.TechnicalManual,
            Id: "technical-manual",
            Label: "Technical Manual",
            DemoTitleLines: ["Improved", "Db"],
            DemoTitleY: 106,
            DemoTitleDy: "1.18em",
            DemoTitleFontSize: "11",
            DemoTitleFill: "#1f2937",
            Note: "Manual/reference cover with balanced face lines and distinct page tabs.",
            CoverColors: new("#4d7c0f", "#365314", "#1a2e05"),
            PageColors: new("#fefce8", "#eee8c9", "#d6d3d1"),
            CoverPath: "M26 18h85c14 0 25 12 25 27v126c0 15-11 27-25 27H26c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M109 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#9b958c",
            Plate: new(35, 77, 86, 66, 7, 41, 83, 74, 54, 5, 78, "#f7fee7", "#d9f99d")),
        new(
            Kind: BookCoverDesignKind.DecorativeHardcover,
            Id: "decorative-hardcover",
            Label: "Decorative Hardcover",
            DemoTitleLines: ["Trace", "Back"],
            DemoTitleY: 103,
            DemoTitleDy: "1.2em",
            DemoTitleFontSize: "11.5",
            DemoTitleFill: "#111827",
            Note: "Decorative hardcover with centered gold ornaments outside the protected title plate.",
            CoverColors: new("#4338ca", "#581c87", "#2e1065"),
            PageColors: new("#fff7ed", "#f1e7d7", "#d6d3d1"),
            CoverPath: "M26 18h85c14 0 25 12 25 27v126c0 15-11 27-25 27H26c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M109 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#a99f91",
            Plate: new(35, 76, 86, 68, 10, 41, 82, 74, 56, 7, 78, "#eef2ff", "#c7d2fe")),
        new(
            Kind: BookCoverDesignKind.FieldNotebook,
            Id: "field-notebook",
            Label: "Field Notebook",
            DemoTitleLines: ["Designing", "Reliable", "Systems"],
            DemoTitleY: 95,
            DemoTitleDy: "1.18em",
            DemoTitleFontSize: "11",
            DemoTitleFill: "#111827",
            Note: "Notebook-inspired cover with balanced ruling, dot markers, and four page tabs.",
            CoverColors: new("#0f766e", "#0f766e", "#134e4a"),
            PageColors: new("#fff9ed", "#f4ead9", "#d8d0c4"),
            CoverPath: "M27 18h84c14 0 25 12 25 27v126c0 15-11 27-25 27H27c-12 0-22-10-22-22V40c0-12 10-22 22-22z",
            PagePath: "M109 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z",
            LineStroke: "#a8a29e",
            Plate: new(34, 74, 88, 72, 10, 40, 80, 76, 60, 7, 78, "#f0fdfa", "#ccfbf1"))
    ];
}

public sealed record BookCoverDesignDefinition(
    BookCoverDesignKind Kind,
    string Id,
    string Label,
    IReadOnlyList<string> DemoTitleLines,
    int DemoTitleY,
    string DemoTitleDy,
    string DemoTitleFontSize,
    string DemoTitleFill,
    string Note,
    BookCoverDesignColors CoverColors,
    BookCoverDesignColors PageColors,
    string CoverPath,
    string PagePath,
    string LineStroke,
    BookCoverTitlePlate Plate);

public sealed record BookCoverDesignColors(string Start, string Middle, string End);

public sealed record BookCoverTitlePlate(
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

public enum BookCoverDesignKind
{
    ClothHardback,
    TechnicalManual,
    DecorativeHardcover,
    FieldNotebook
}
