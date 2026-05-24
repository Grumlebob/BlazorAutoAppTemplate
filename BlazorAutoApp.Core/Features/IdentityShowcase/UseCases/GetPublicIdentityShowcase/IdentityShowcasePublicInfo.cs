namespace BlazorAutoApp.Core.Features.IdentityShowcase.UseCases.GetPublicIdentityShowcase;

public class IdentityShowcasePublicInfo
{
    public string AppName { get; set; } = "BlazorAutoApp";
    public string Message { get; set; } = "Identity pipeline is online.";
    public DateTimeOffset ServerTimeUtc { get; set; }
}
