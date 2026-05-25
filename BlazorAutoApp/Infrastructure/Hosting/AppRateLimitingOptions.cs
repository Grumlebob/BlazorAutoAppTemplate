namespace BlazorAutoApp.Infrastructure.Hosting;

internal sealed class AppRateLimitingOptions
{
    public const string SectionName = "RateLimiting";

    public RateLimitRuleOptions Global { get; set; } = new()
    {
        PermitLimit = 600,
        WindowSeconds = 60,
        QueueLimit = 0
    };

    public RateLimitRuleOptions Api { get; set; } = new()
    {
        PermitLimit = 60,
        WindowSeconds = 60,
        QueueLimit = 0
    };

    public RateLimitRuleOptions Authentication { get; set; } = new()
    {
        PermitLimit = 120,
        WindowSeconds = 300,
        QueueLimit = 0
    };

    public bool AllRulesAreValid()
    {
        return Global.IsValid() && Api.IsValid() && Authentication.IsValid();
    }
}

internal sealed class RateLimitRuleOptions
{
    public int PermitLimit { get; set; }

    public int WindowSeconds { get; set; }

    public int QueueLimit { get; set; }

    public bool IsValid()
    {
        return PermitLimit > 0 && WindowSeconds > 0 && QueueLimit >= 0;
    }
}
