namespace BlazorAutoApp.Features.Login.Accounts.Email;

internal enum AccountMailPurpose
{
    Confirmation,
    PasswordReset,
    EmailChange
}

internal sealed record AccountMailPayload(
    int Version,
    string Recipient,
    string UserId,
    AccountMailPurpose Purpose,
    string SecurityStamp,
    string Token,
    string? TargetEmail,
    DateTimeOffset LinkExpiresUtc);

internal sealed record AccountMailMessage(string MessageId, string Recipient, string Subject, string Text);

internal interface IAccountMailFrontend
{
    bool UsesFragmentSecrets { get; }
    string GetRoute(AccountMailPurpose purpose);
}

internal sealed class AccountMailFrontend(bool usesFragmentSecrets) : IAccountMailFrontend
{
    public static AccountMailFrontend React { get; } = new(usesFragmentSecrets: true);
    public static AccountMailFrontend BlazorAuto { get; } = new(usesFragmentSecrets: false);

    public bool UsesFragmentSecrets { get; } = usesFragmentSecrets;

    public string GetRoute(AccountMailPurpose purpose) => (UsesFragmentSecrets, purpose) switch
    {
        (true, AccountMailPurpose.Confirmation) => "auth/confirm-email",
        (true, AccountMailPurpose.PasswordReset) => "auth/reset-password",
        (true, AccountMailPurpose.EmailChange) => "auth/confirm-email-change",
        (false, AccountMailPurpose.Confirmation) => "Account/ConfirmEmail",
        (false, AccountMailPurpose.PasswordReset) => "Account/ResetPassword",
        (false, AccountMailPurpose.EmailChange) => "Account/ConfirmEmailChange",
        _ => throw new ArgumentOutOfRangeException(nameof(purpose))
    };
}

internal interface IAccountMailTransport
{
    Task SendAsync(AccountMailMessage message, CancellationToken cancellationToken);
}
