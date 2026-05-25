namespace BlazorAutoApp.Core.Features.Books.UseCases.Shared;

public static class BookUrlValidation
{
    public static bool IsValidOptionalHttpUrl(string? url)
    {
        if (string.IsNullOrWhiteSpace(url))
        {
            return true;
        }

        return Uri.TryCreate(url.Trim(), UriKind.Absolute, out var parsed)
            && (parsed.Scheme == Uri.UriSchemeHttp || parsed.Scheme == Uri.UriSchemeHttps);
    }
}
