namespace BlazorAutoApp.Test.E2E.Support;

public sealed record ResponsiveViewport(string Label, int Width, int Height)
{
    public static readonly ResponsiveViewport DesktopReview = new("1280x900", 1280, 900);
    public static readonly ResponsiveViewport Desktop = new("1440x1000", 1440, 1000);
    public static readonly ResponsiveViewport Laptop = new("1366x768", 1366, 768);
    public static readonly ResponsiveViewport WideDesktop = new("1920x1080", 1920, 1080);
    public static readonly ResponsiveViewport TabletPortrait = new("768x1024", 768, 1024);
    public static readonly ResponsiveViewport TabletLandscape = new("1024x768", 1024, 768);
    public static readonly ResponsiveViewport Mobile = new("390x844", 390, 844);
    public static readonly ResponsiveViewport UltraNarrowMobile = new("320x844", 320, 844);
    public static readonly ResponsiveViewport LargeMobile = new("430x932", 430, 932);
    public static readonly ResponsiveViewport NarrowMobile = new("360x740", 360, 740);
    public static readonly ResponsiveViewport MobileLandscape = new("844x390", 844, 390);

    public static IReadOnlyList<ResponsiveViewport> PrimaryReview { get; } =
    [
        DesktopReview,
        Mobile
    ];

    public static IReadOnlyList<ResponsiveViewport> FullMatrix { get; } =
    [
        DesktopReview,
        Desktop,
        Laptop,
        WideDesktop,
        TabletPortrait,
        TabletLandscape,
        Mobile,
        UltraNarrowMobile,
        LargeMobile,
        NarrowMobile,
        MobileLandscape
    ];
}
