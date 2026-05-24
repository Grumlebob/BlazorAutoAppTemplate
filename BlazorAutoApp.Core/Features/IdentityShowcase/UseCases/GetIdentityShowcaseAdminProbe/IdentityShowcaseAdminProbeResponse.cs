namespace BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetIdentityShowcaseAdminProbe;

public class IdentityShowcaseAdminProbeResponse
{
    public bool Success { get; set; }
    public string Message { get; set; } = "";
    public string[] Roles { get; set; } = [];
    public DateTimeOffset ServerTimeUtc { get; set; }
}
