namespace BlazorAutoApp.Client.Features.Books.Shared;

public static class BookCoverDesignCatalog
{
    public static IReadOnlyList<BookCoverDesignDefinition> All { get; } =
    [
        new(
            Kind: BookCoverDesignKind.ClothHardback,
            Id: "cloth-hardback",
            Label: "Cloth Hardback",
            Plate: BookCoverGeometry.CenteredPlate(62, 94, 88, 11, "#f8fafc", "#e0f2fe")),
        new(
            Kind: BookCoverDesignKind.DecorativeHardcover,
            Id: "decorative-hardcover",
            Label: "Decorative Hardcover",
            Plate: BookCoverGeometry.CenteredPlate(76, 86, 68, 10, "#f8fafc", "#f4d27a")),
        new(
            Kind: BookCoverDesignKind.FieldNotebook,
            Id: "field-notebook",
            Label: "Field Notebook",
            Plate: BookCoverGeometry.CenteredPlate(74, 88, 72, 10, "#f0fdfa", "#ccfbf1")),
        new(
            Kind: BookCoverDesignKind.PrismAtlas,
            Id: "prism-atlas",
            Label: "Prism Atlas",
            Plate: BookCoverGeometry.CenteredPlate(76, 86, 68, 8, "#f8fafc", "#67e8f9")),
        new(
            Kind: BookCoverDesignKind.DropletMonograph,
            Id: "droplet-monograph",
            Label: "Droplet Monograph",
            Plate: BookCoverGeometry.CenteredPlate(76, 88, 68, 12, "#f8fafc", "#67e8f9")),
        new(
            Kind: BookCoverDesignKind.TransitMapFolio,
            Id: "transit-map-folio",
            Label: "Transit Map Folio",
            Plate: BookCoverGeometry.CenteredPlate(76, 86, 68, 10, "#f8fafc", "#facc15")),
        new(
            Kind: BookCoverDesignKind.CompassFieldbook,
            Id: "compass-fieldbook",
            Label: "Compass Fieldbook",
            Plate: BookCoverGeometry.CenteredPlate(76, 86, 68, 8, "#f8fafc", "#fbbf24")),
        new(
            Kind: BookCoverDesignKind.AtlasPinboard,
            Id: "atlas-pinboard",
            Label: "Atlas Pinboard",
            Plate: BookCoverGeometry.CenteredPlate(76, 88, 68, 9, "#fffbeb", "#facc15")),
        new(
            Kind: BookCoverDesignKind.SeismographLog,
            Id: "seismograph-log",
            Label: "Seismograph Log",
            Plate: BookCoverGeometry.CenteredPlate(76, 88, 68, 9, "#fff7ed", "#fecaca")),
        new(
            Kind: BookCoverDesignKind.AlpineTrailGuide,
            Id: "alpine-trail-guide",
            Label: "Alpine Trail Guide",
            Plate: BookCoverGeometry.CenteredPlate(76, 88, 68, 10, "#f7fee7", "#bef264"))
    ];
}

public sealed record BookCoverDesignDefinition(
    BookCoverDesignKind Kind,
    string Id,
    string Label,
    BookCoverTitlePlate Plate);

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
    DecorativeHardcover,
    FieldNotebook,
    PrismAtlas,
    DropletMonograph,
    TransitMapFolio,
    CompassFieldbook,
    AtlasPinboard,
    SeismographLog,
    AlpineTrailGuide
}
