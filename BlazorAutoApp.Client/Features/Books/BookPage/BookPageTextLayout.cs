namespace BlazorAutoApp.Client.Features.Books.BookPage;

internal static class BookPageTextLayout
{
    private const int MaxTitleLineLength = 12;
    private const int MaxTitleLines = 3;
    private const int MaxAuthorLength = 28;

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
                lines.Add(TrimLine(current, MaxTitleLineLength));
            }

            current = word;
            if (lines.Count == MaxTitleLines - 1)
            {
                break;
            }
        }

        if (current.Length > 0 && lines.Count < MaxTitleLines)
        {
            lines.Add(TrimLine(current, MaxTitleLineLength));
        }

        return lines.Count == 0 ? ["Untitled"] : lines;
    }

    public static string AuthorLine(string? author)
    {
        var clean = string.IsNullOrWhiteSpace(author) ? "Unknown author" : author.Trim();
        return TrimLine(clean, MaxAuthorLength);
    }

    private static string TrimLine(string value, int maxLength) =>
        value.Length <= maxLength ? value : value[..(maxLength - 1)] + ".";
}
