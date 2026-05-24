using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetIdentityShowcaseAdminProbe;
using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetPublicIdentityShowcase;
using BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetSecureIdentityShowcase;

namespace BlazorAutoApp.Core.Features.IdentityShowcase.Contracts;

public interface IIdentityShowcaseApi
{
    Task<IdentityShowcasePublicInfo> GetPublicAsync(CancellationToken ct = default);
    Task<IdentityShowcaseSecureInfo?> GetSecureAsync(CancellationToken ct = default);
    Task<IdentityShowcaseAdminProbeResponse> GetAdminProbeAsync(CancellationToken ct = default);
}
