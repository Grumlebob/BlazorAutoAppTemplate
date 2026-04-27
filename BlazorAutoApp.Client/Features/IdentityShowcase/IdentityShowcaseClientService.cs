using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.IdentityShowcase;

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
}
