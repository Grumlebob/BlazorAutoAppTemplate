namespace BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetSecureIdentityShowcase;

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
