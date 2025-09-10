using System.Net;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Email;

namespace BlazorAutoApp.Client.Services;

public class SendEmailClientService : IEmailApi
{
    private readonly HttpClient _http;

    public SendEmailClientService(HttpClient http)
    {
        _http = http;
    }

    public async Task<SendEmailResponse> SendAsync(SendEmailRequest req, CancellationToken ct = default)
    {
        var httpResponse = await _http.PostAsJsonAsync("api/email/send", req, ct);

        // Try to read a typed payload if the server sent one
        SendEmailResponse? payload = null;
        try
        {
            payload = await httpResponse.Content.ReadFromJsonAsync<SendEmailResponse>(cancellationToken: ct);
        }
        catch
        {
            // If it's not JSON (e.g., "Missing 'To'"), we'll handle below.
        }

        if (httpResponse.StatusCode == HttpStatusCode.Accepted)
        {
            // Success path: server returns 202 with a SendEmailResponse body.
            return payload ?? new SendEmailResponse { Success = true };
        }

        // On errors (e.g., 400), prefer the typed payload if available.
        if (payload is not null)
        {
            return payload;
        }

        // Fallback: read plain text error or synthesize a message.
        var text = await httpResponse.Content.ReadAsStringAsync(ct);
        var error = string.IsNullOrWhiteSpace(text)
            ? $"{(int)httpResponse.StatusCode} {httpResponse.ReasonPhrase}"
            : text;

        return new SendEmailResponse { Success = false, Error = error };
    }
}