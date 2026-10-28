using System.Net.Http.Json;
using System.Security.Claims;
using GrumPlates.Core.Features.Accounts.Contracts;
using Microsoft.AspNetCore.Components.Authorization;

namespace GrumPlates.Client.Features.Books;

/// <summary>Applies shared account CSRF and captured-owner headers to the retained Blazor Books client.</summary>
public sealed class BooksAntiforgeryHandler(AuthenticationStateProvider authenticationStateProvider) : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        if (!IsBooksRequest(request.RequestUri))
        {
            return await base.SendAsync(request, cancellationToken);
        }

        // Capture the owner before any network request. A later session refresh must not
        // silently change the owner associated with this Books operation.
        var authentication = await authenticationStateProvider.GetAuthenticationStateAsync();
        var capturedUserId = GetImmutableUserId(authentication.User);

        var configurationUri = new Uri(request.RequestUri!, "/api/client-config");
        using var configurationRequest = new HttpRequestMessage(HttpMethod.Get, configurationUri);
        using var configurationResponse = await base.SendAsync(configurationRequest, cancellationToken);
        configurationResponse.EnsureSuccessStatusCode();
        var clientConfiguration = await configurationResponse.Content.ReadFromJsonAsync<ClientConfiguration>(cancellationToken);
        if (clientConfiguration is not { SchemaVersion: 1, ApplicationId.Length: > 0 })
        {
            throw new InvalidDataException("The application client configuration is unavailable.");
        }

        if (!clientConfiguration.AccountsEnabled)
        {
            return await base.SendAsync(request, cancellationToken);
        }

        request.Headers.Remove("X-Expected-User");
        if (!string.IsNullOrEmpty(capturedUserId))
        {
            request.Headers.TryAddWithoutValidation("X-Expected-User", capturedUserId);
        }

        if (request.Method != HttpMethod.Get && request.Method != HttpMethod.Head)
        {
            var sessionUri = new Uri(request.RequestUri!, "/api/auth/session");
            using var sessionRequest = new HttpRequestMessage(HttpMethod.Get, sessionUri);
            using var sessionResponse = await base.SendAsync(sessionRequest, cancellationToken);
            sessionResponse.EnsureSuccessStatusCode();
            var session = await sessionResponse.Content.ReadFromJsonAsync<AccountSession>(cancellationToken);
            if (session is not { Enabled: true, CsrfToken.Length: > 0 })
            {
                throw new InvalidDataException("The account session is unavailable.");
            }
            request.Headers.Remove("X-CSRF-TOKEN");
            request.Headers.TryAddWithoutValidation("X-CSRF-TOKEN", session.CsrfToken);
        }

        return await base.SendAsync(request, cancellationToken);
    }

    private static bool IsBooksRequest(Uri? requestUri) => requestUri is not null
        && requestUri.AbsolutePath.StartsWith("/api/books", StringComparison.OrdinalIgnoreCase);

    private static string? GetImmutableUserId(ClaimsPrincipal user)
    {
        if (user.Identity?.IsAuthenticated != true)
        {
            return null;
        }

        return user.FindFirst(ClaimTypes.NameIdentifier)?.Value ?? user.FindFirst("sub")?.Value;
    }
}
