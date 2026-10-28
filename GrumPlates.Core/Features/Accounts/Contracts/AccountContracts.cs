using System.ComponentModel.DataAnnotations;

namespace GrumPlates.Core.Features.Accounts.Contracts;

public sealed record ClientConfiguration(int SchemaVersion, bool AccountsEnabled, string ApplicationId);
public sealed record AccountProfile(string Id, string Email, IReadOnlyList<string> Roles);
public sealed record AccountSession(bool Enabled, bool RegistrationEnabled, bool EmailEnabled, string CsrfToken, AccountProfile? User);
public sealed record AccountMessage(string Message);

public class AccountEmailRequest
{
    [Required, EmailAddress, StringLength(254)]
    public string Email { get; set; } = "";
}

public sealed class AccountLoginRequest : AccountEmailRequest
{
    [Required(AllowEmptyStrings = true), StringLength(256, MinimumLength = 1)]
    public string Password { get; set; } = "";
    public bool RememberMe { get; set; }
}

public sealed class AccountRegisterRequest : AccountEmailRequest
{
}

public class AccountPasswordRequest
{
    [Required(AllowEmptyStrings = true), StringLength(256, MinimumLength = 1)]
    public string Password { get; set; } = "";
}

public sealed class AccountChangePasswordRequest : AccountPasswordRequest
{
    [Required(AllowEmptyStrings = true), StringLength(256, MinimumLength = 1)]
    public string NewPassword { get; set; } = "";
}

public sealed class AccountChangeEmailRequest : AccountPasswordRequest
{
    [Required, EmailAddress, StringLength(254)]
    public string Email { get; set; } = "";
}

public class AccountTokenRequest
{
    [Required, StringLength(128)]
    public string UserId { get; set; } = "";
    [Required, StringLength(4096)]
    public string Token { get; set; } = "";
}

public sealed class AccountConfirmEmailRequest : AccountTokenRequest
{
    [Required(AllowEmptyStrings = true), StringLength(256, MinimumLength = 1)]
    public string NewPassword { get; set; } = "";
}

public sealed class AccountResetPasswordRequest : AccountTokenRequest
{
    [Required(AllowEmptyStrings = true), StringLength(256, MinimumLength = 1)]
    public string NewPassword { get; set; } = "";
}

public sealed class AccountConfirmEmailChangeRequest : AccountTokenRequest
{
    [Required, EmailAddress, StringLength(254)]
    public string Email { get; set; } = "";
}

public sealed record AccountExport(AccountProfile User, IReadOnlyList<AccountExportBook> Books);
public sealed record AccountExportBook(int Id, string Title, string? Author, string? Url);
