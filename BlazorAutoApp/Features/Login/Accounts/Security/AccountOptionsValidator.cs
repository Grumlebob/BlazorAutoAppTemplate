using System.ComponentModel.DataAnnotations;
using Microsoft.Extensions.Options;

namespace BlazorAutoApp.Features.Login.Accounts.Security;

internal sealed class AccountOptionsValidator(string appName) : IValidateOptions<AccountOptions>
{
    public ValidateOptionsResult Validate(string? name, AccountOptions options)
    {
        if (options.Email is null || options.AdminSeed is null || options.WriteLimit is null)
        {
            return ValidateOptionsResult.Fail("Accounts:Email, Accounts:AdminSeed and Accounts:WriteLimit must be configuration objects.");
        }
        List<string> errors = [];
        ValidateSeed(options, errors);
        ValidateEmail(options, errors);
        if (options.RegistrationEnabled && (!options.Enabled || !options.EmailEnabled))
        {
            errors.Add("Accounts:RegistrationEnabled requires Accounts:Enabled and Accounts:Email:Host.");
        }
        if (options.WriteLimit.PermitLimit <= 0)
        {
            errors.Add("Accounts:WriteLimit:PermitLimit must be positive.");
        }
        if (options.WriteLimit.WindowSeconds <= 0)
        {
            errors.Add("Accounts:WriteLimit:WindowSeconds must be positive.");
        }
        if (!string.IsNullOrEmpty(options.PublicOrigin) && !IsBareHttpsOrigin(options.PublicOrigin))
        {
            errors.Add("Accounts:PublicOrigin must be a bare HTTPS origin.");
        }
        return errors.Count == 0 ? ValidateOptionsResult.Success : ValidateOptionsResult.Fail(errors);
    }

    private void ValidateSeed(AccountOptions options, List<string> errors)
    {
        var seed = options.AdminSeed;
        if (string.IsNullOrEmpty(seed.Email) != string.IsNullOrEmpty(seed.Password))
        {
            errors.Add("Accounts:AdminSeed:Email and Accounts:AdminSeed:Password must be supplied together.");
        }
        if ((!string.IsNullOrEmpty(seed.Email) || seed.Enabled) && !IsEmail(seed.Email))
        {
            errors.Add("Accounts:AdminSeed:Email must be a valid mailbox.");
        }
        if (seed.Enabled && !options.Enabled)
        {
            errors.Add("Accounts:AdminSeed:Enabled requires Accounts:Enabled.");
        }
        if (seed.Enabled && string.IsNullOrEmpty(seed.Password))
        {
            errors.Add("Accounts:AdminSeed:Password is required.");
        }
        if (seed.Enabled && !AccountPasswordValidator.ValidateCandidate(seed.Password, seed.Email, appName).Succeeded)
        {
            errors.Add("Accounts:AdminSeed:Password must satisfy the account password policy.");
        }
    }

    private static void ValidateEmail(AccountOptions options, List<string> errors)
    {
        var email = options.Email;
        var hasHost = !string.IsNullOrWhiteSpace(email.Host);
        if (!string.IsNullOrEmpty(email.Host) && (email.Host != email.Host.Trim() || Uri.CheckHostName(email.Host) == UriHostNameType.Unknown))
        {
            errors.Add("Accounts:Email:Host must be a DNS name or IP address.");
        }
        if (hasHost && !options.Enabled)
        {
            errors.Add("Accounts:Email:Host requires Accounts:Enabled.");
        }
        if (!hasHost && (!string.IsNullOrEmpty(email.From) || !string.IsNullOrEmpty(email.Username) || !string.IsNullOrEmpty(email.Password)))
        {
            errors.Add("Accounts:Email:Host is required when mail settings are supplied.");
        }
        if (hasHost && (!IsEmail(email.From) || !IsBareHttpsOrigin(options.PublicOrigin)))
        {
            errors.Add("Accounts:Email:From and Accounts:PublicOrigin must be configured for email.");
        }
        if (email.Port is < 1 or > 65535)
        {
            errors.Add("Accounts:Email:Port must be between 1 and 65535.");
        }
        if (email.Security is not ("StartTls" or "SslOnConnect"))
        {
            errors.Add("Accounts:Email:Security must be StartTls or SslOnConnect.");
        }
        if (string.IsNullOrEmpty(email.Username) != string.IsNullOrEmpty(email.Password))
        {
            errors.Add("Accounts:Email:Username and Accounts:Email:Password must be supplied together.");
        }
        if (email.MaxAttempts is < 1 or > 5)
        {
            errors.Add("Accounts:Email:MaxAttempts must be between 1 and 5.");
        }
    }

    private static bool IsEmail(string? value) => value is { Length: > 0 and <= 254 }
        && !value.Any(char.IsControl) && value == value.Trim() && new EmailAddressAttribute().IsValid(value);

    private static bool IsBareHttpsOrigin(string? value) => !string.IsNullOrEmpty(value) && value == value.Trim()
        && !value.Any(char.IsControl) && !value.Contains('\\')
        && !value.Contains('?') && !value.Contains('#')
        && value.StartsWith("https://", StringComparison.OrdinalIgnoreCase)
        && (value.IndexOf('/', 8) < 0 || value.IndexOf('/', 8) == value.Length - 1)
        && Uri.TryCreate(value, UriKind.Absolute, out var uri)
        && uri.Scheme == Uri.UriSchemeHttps && !string.IsNullOrEmpty(uri.Host)
        && string.IsNullOrEmpty(uri.UserInfo) && uri.AbsolutePath == "/"
        && string.IsNullOrEmpty(uri.Query) && string.IsNullOrEmpty(uri.Fragment);
}
