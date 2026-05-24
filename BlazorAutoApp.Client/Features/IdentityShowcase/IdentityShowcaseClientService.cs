using System.Net;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.IdentityShowcase.Contracts;
using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetIdentityShowcaseAdminProbe;
using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetPublicIdentityShowcase;
using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetSecureIdentityShowcase;

namespace BlazorAutoApp.Client.Features.IdentityShowcase;

public class IdentityShowcaseClientService(HttpClient http) : IIdentityShowcaseApi
{
    public async Task<IdentityShowcasePublicInfo> GetPublicAsync(CancellationToken ct = default)
    {
        try
        {
            var result = await http.GetFromJsonAsync<IdentityShowcasePublicInfo>("api/identity-showcase/public", ct);
            return result ?? new IdentityShowcasePublicInfo
            {
                AppName = "BlazorAutoApp",
                Message = "Public identity showcase endpoint returned an empty payload.",
                ServerTimeUtc = DateTimeOffset.UtcNow
            };
        }
        catch
        {
            return new IdentityShowcasePublicInfo
            {
                AppName = "BlazorAutoApp",
                Message = "Public identity showcase endpoint is currently unavailable.",
                ServerTimeUtc = DateTimeOffset.UtcNow
            };
        }
    }

    public async Task<IdentityShowcaseSecureInfo?> GetSecureAsync(CancellationToken ct = default)
    {
        try
        {
            using var response = await http.GetAsync("api/identity-showcase/secure", ct);
            if (!response.IsSuccessStatusCode)
            {
                return null;
            }

            return await response.Content.ReadFromJsonAsync<IdentityShowcaseSecureInfo>(cancellationToken: ct);
        }
        catch
        {
            return null;
        }
    }

    public async Task<IdentityShowcaseAdminProbeResponse> GetAdminProbeAsync(CancellationToken ct = default)
    {
        try
        {
            using var response = await http.GetAsync("api/identity-showcase/admin-probe", ct);

            if (response.StatusCode == HttpStatusCode.Forbidden)
            {
                return new IdentityShowcaseAdminProbeResponse
                {
                    Success = false,
                    Message = "Admin probe denied (403). You are signed in but missing the Admin role.",
                    ServerTimeUtc = DateTimeOffset.UtcNow
                };
            }

            if (response.StatusCode == HttpStatusCode.Unauthorized)
            {
                return new IdentityShowcaseAdminProbeResponse
                {
                    Success = false,
                    Message = "Admin probe requires login.",
                    ServerTimeUtc = DateTimeOffset.UtcNow
                };
            }

            if (!response.IsSuccessStatusCode)
            {
                return new IdentityShowcaseAdminProbeResponse
                {
                    Success = false,
                    Message = $"Admin probe failed with HTTP {(int)response.StatusCode}.",
                    ServerTimeUtc = DateTimeOffset.UtcNow
                };
            }

            var parsed = await response.Content.ReadFromJsonAsync<IdentityShowcaseAdminProbeResponse>(cancellationToken: ct);
            return parsed ?? new IdentityShowcaseAdminProbeResponse
            {
                Success = false,
                Message = "Admin probe returned an empty payload.",
                ServerTimeUtc = DateTimeOffset.UtcNow
            };
        }
        catch
        {
            return new IdentityShowcaseAdminProbeResponse
            {
                Success = false,
                Message = "Admin probe redirected or failed unexpectedly.",
                ServerTimeUtc = DateTimeOffset.UtcNow
            };
        }
    }
}
