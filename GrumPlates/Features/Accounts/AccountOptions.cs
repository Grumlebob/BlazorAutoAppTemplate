namespace GrumPlates.Features.Accounts;

// Bind once during composition. Routing, policies and workers share this snapshot.
internal sealed class AccountOptions
{
    public bool Enabled { get; init; }
    public bool RegistrationEnabled { get; init; }
    public string PublicOrigin { get; init; } = "";
    public AccountEmailOptions Email { get; init; } = new();
    public AdminSeedOptions AdminSeed { get; init; } = new();
    public AccountWriteLimitOptions WriteLimit { get; init; } = new();
    public bool EmailEnabled => Enabled && !string.IsNullOrWhiteSpace(Email.Host);
}

internal sealed class AccountEmailOptions
{
    public string Host { get; init; } = "";
    public int Port { get; init; } = 587;
    public string Security { get; init; } = "StartTls";
    public string Username { get; init; } = "";
    public string Password { get; init; } = "";
    public string From { get; init; } = "";
    public int MaxAttempts { get; init; } = 3;
}

internal sealed class AdminSeedOptions
{
    public bool Enabled { get; init; }
    public string Email { get; init; } = "";
    public string Password { get; init; } = "";
}

internal sealed class AccountWriteLimitOptions
{
    public int PermitLimit { get; init; } = 20;
    public int WindowSeconds { get; init; } = 300;
}
