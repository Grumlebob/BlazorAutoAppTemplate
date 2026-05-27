namespace BlazorAutoApp.Client.Features.Books.BookModal;

public sealed record BookModalRouteState(BookModalSource Source, BookModalMode Mode, int? AuthorBookId, int? UserBookId)
{
    public string EditorRequestKey => Mode switch
    {
        BookModalMode.Create => "user:create",
        BookModalMode.Edit when UserBookId is { } id => $"user:edit:{id.ToString(System.Globalization.CultureInfo.InvariantCulture)}",
        _ => "none"
    };

    public static BookModalRouteState? Parse(string uri)
    {
        var absoluteUri = new Uri(uri);
        var query = ParseQuery(absoluteUri.Query);

        if (!query.TryGetValue("bookMode", out var modeValue) || !TryParseMode(modeValue, out var mode))
        {
            return null;
        }

        if (mode is BookModalMode.Create)
        {
            return new BookModalRouteState(BookModalSource.User, mode, null, null);
        }

        if (query.TryGetValue("authorBookId", out var authorBookId) &&
            int.TryParse(authorBookId, System.Globalization.NumberStyles.Integer, System.Globalization.CultureInfo.InvariantCulture, out var catalogId))
        {
            return new BookModalRouteState(BookModalSource.Author, mode, catalogId, null);
        }

        if (query.TryGetValue("bookId", out var bookId) &&
            int.TryParse(bookId, System.Globalization.NumberStyles.Integer, System.Globalization.CultureInfo.InvariantCulture, out var id))
        {
            return new BookModalRouteState(BookModalSource.User, mode, null, id);
        }

        return new BookModalRouteState(BookModalSource.User, mode, null, null);
    }

    private static Dictionary<string, string> ParseQuery(string query)
    {
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var segment in query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var parts = segment.Split('=', 2);
            if (parts.Length == 0 || string.IsNullOrWhiteSpace(parts[0]))
            {
                continue;
            }

            var key = Decode(parts[0]);
            var value = parts.Length == 2 ? Decode(parts[1]) : string.Empty;
            result[key] = value;
        }

        return result;
    }

    private static string Decode(string value) =>
        Uri.UnescapeDataString(value.Replace("+", " ", StringComparison.Ordinal));

    private static bool TryParseMode(string value, out BookModalMode mode)
    {
        var normalized = value.ToLowerInvariant();
        mode = normalized switch
        {
            "view" => BookModalMode.View,
            "edit" => BookModalMode.Edit,
            "create" => BookModalMode.Create,
            _ => default
        };

        return normalized is "view" or "edit" or "create";
    }
}

public enum BookModalSource
{
    Author,
    User
}

public enum BookModalMode
{
    View,
    Edit,
    Create
}
