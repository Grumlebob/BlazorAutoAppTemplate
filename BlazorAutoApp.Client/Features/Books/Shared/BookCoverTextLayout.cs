namespace BlazorAutoApp.Client.Features.Books.Shared;

internal static class BookCoverTextLayout
{
    private const int MaxTitleLineLength = 12;
    private const int MaxTitleLines = 3;

    public static IReadOnlyList<string> TitleLines(string? title)
    {
        var clean = string.IsNullOrWhiteSpace(title) ? "Untitled" : title.Trim();
        var words = clean.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var lines = new List<string>();
        var current = string.Empty;

        foreach (var word in words)
        {
            var candidate = current.Length == 0 ? word : $"{current} {word}";
            if (candidate.Length <= MaxTitleLineLength)
            {
                current = candidate;
                continue;
            }

            if (current.Length > 0)
            {
                lines.Add(TrimLine(current));
            }

            current = word;
            if (lines.Count == MaxTitleLines - 1)
            {
                break;
            }
        }

        if (current.Length > 0 && lines.Count < MaxTitleLines)
        {
            lines.Add(TrimLine(current));
        }

        return lines.Count == 0 ? ["Untitled"] : lines;
    }

    private static string TrimLine(string value) =>
        value.Length <= MaxTitleLineLength ? value : value[..(MaxTitleLineLength - 1)] + ".";
}
