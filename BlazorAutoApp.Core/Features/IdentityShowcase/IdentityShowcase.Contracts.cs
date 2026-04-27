namespace BlazorAutoApp.Core.Features.IdentityShowcase;

public interface IIdentityShowcaseApi
{
    Task<IdentityShowcasePublicInfo> GetPublicAsync(CancellationToken ct = default);
    Task<IdentityShowcaseSecureInfo?> GetSecureAsync(CancellationToken ct = default);
    Task<IdentityShowcaseAdminProbeResponse> GetAdminProbeAsync(CancellationToken ct = default);
}

public class IdentityShowcasePublicInfo
{
    public string AppName { get; set; } = "BlazorAutoApp";
    public string Message { get; set; } = "Identity pipeline is online.";
    public DateTimeOffset ServerTimeUtc { get; set; }
}

public class IdentityShowcaseSecureInfo
{
    public bool IsAuthenticated { get; set; }
    public string UserName { get; set; } = "";
    public string UserId { get; set; } = "";
    public string AuthenticationType { get; set; } = "";
    public int ClaimCount { get; set; }
    public bool HasAnyRole { get; set; }
    public bool IsAdmin { get; set; }
    public bool IsViewer { get; set; }
    public string[] Roles { get; set; } = [];
    public DateTimeOffset ServerTimeUtc { get; set; }
}

public class IdentityShowcaseAdminProbeResponse
{
    public bool Success { get; set; }
    public string Message { get; set; } = "";
    public string[] Roles { get; set; } = [];
    public DateTimeOffset ServerTimeUtc { get; set; }
}
