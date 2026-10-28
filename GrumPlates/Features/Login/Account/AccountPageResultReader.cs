using System.Text.Json;

namespace GrumPlates.Features.Login.Account;

internal static class AccountPageResultReader
{
    public static async Task<(int StatusCode, string Body)> ReadAsync(HttpContext source, IResult result)
    {
        await using var body = new MemoryStream();
        var response = new DefaultHttpContext
        {
            RequestServices = source.RequestServices
        };
        response.Response.Body = body;
        await result.ExecuteAsync(response);
        body.Position = 0;
        using var reader = new StreamReader(body);
        return (response.Response.StatusCode, await reader.ReadToEndAsync(source.RequestAborted));
    }

    public static string Message(string body, string fallback)
    {
        try
        {
            using var json = JsonDocument.Parse(body);
            if (json.RootElement.TryGetProperty("message", out var message)
                && message.ValueKind == JsonValueKind.String)
            {
                return message.GetString() ?? fallback;
            }
            if (json.RootElement.TryGetProperty("detail", out var detail)
                && detail.ValueKind == JsonValueKind.String)
            {
                return detail.GetString() ?? fallback;
            }
        }
        catch (JsonException)
        {
            // The component shows fixed safe text when an operation has no JSON response.
        }
        return fallback;
    }
}
