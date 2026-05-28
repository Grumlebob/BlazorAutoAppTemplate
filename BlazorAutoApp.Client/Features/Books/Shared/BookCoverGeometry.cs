namespace BlazorAutoApp.Client.Features.Books.Shared;

public static class BookCoverGeometry
{
    public const int TitleCenterX = 71;
    public const int CoverSafeLeft = 5;
    public const int CoverSafeRight = 136;

    public const string CoverPath = "M27 18h84c14 0 25 12 25 27v126c0 15-11 27-25 27H27c-12 0-22-10-22-22V40c0-12 10-22 22-22z";

    public const string PagePath = "M109 24h24c16 0 28 12 28 28v116c0 18-12 31-31 31h-21z";

    public const string PageLinesPath =
        "M112 44h38M112 59h36M112 74h39M112 89h37M112 104h39M112 119h36M112 134h38M112 149h36M112 164h39M112 178h37M112 188h34";

    public static BookCoverTitlePlate CenteredPlate(
        int y,
        int width,
        int height,
        int radius,
        string fill,
        string stroke)
    {
        const int innerInset = 6;

        var x = TitleCenterX - (width / 2);
        return new BookCoverTitlePlate(
            x,
            y,
            width,
            height,
            radius,
            x + innerInset,
            y + innerInset,
            width - (innerInset * 2),
            height - (innerInset * 2),
            InnerRadius(radius),
            TitleCenterX,
            fill,
            stroke);
    }

    private static int InnerRadius(int radius) => Math.Max(5, radius - 3);
}
