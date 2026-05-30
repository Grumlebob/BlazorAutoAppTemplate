using System.Net;

namespace BlazorAutoApp.Simulation.Http;

internal static class HttpClientFactory
{
    public static HttpClientHandler CreateHandler(Uri baseUrl, CookieContainer? cookies = null)
    {
        var handler = new HttpClientHandler
        {
            AllowAutoRedirect = true
        };

        if (cookies is not null)
        {
            handler.CookieContainer = cookies;
            handler.UseCookies = true;
        }

        if (IsLocalhost(baseUrl))
        {
            handler.ServerCertificateCustomValidationCallback = HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
        }

        return handler;
    }

    public static bool IsLocalhost(Uri uri) =>
        string.Equals(uri.Host, "localhost", StringComparison.OrdinalIgnoreCase)
        || string.Equals(uri.Host, "127.0.0.1", StringComparison.OrdinalIgnoreCase)
        || string.Equals(uri.Host, "::1", StringComparison.OrdinalIgnoreCase);
}
