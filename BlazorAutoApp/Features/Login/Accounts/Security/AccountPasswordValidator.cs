using System.Buffers;
using System.Collections.Frozen;
using System.Security.Cryptography;
using System.Text;
using BlazorAutoApp.Features.Login.Account;
using Microsoft.AspNetCore.Identity;

namespace BlazorAutoApp.Features.Login.Accounts.Security;

internal sealed class AccountPasswordValidator(AccountApplicationIdentity identity) : IPasswordValidator<ApplicationUser>
{
    internal const string ResourceName = "BlazorAutoApp.Accounts.CommonPasswords";
    internal const string ResourceSha256 = "68782d6a4a19a4768d5f15dd66bd534e7a33055cc755411e33f16d18c50fdcce";
    private static readonly Lazy<FrozenSet<string>> CommonPasswords = new(LoadCommonPasswords);
    private readonly string _appName = identity.AppName;

    public Task<IdentityResult> ValidateAsync(UserManager<ApplicationUser> manager, ApplicationUser user, string? password) =>
        Task.FromResult(ValidateCandidate(password, user.Email, _appName));

    internal static IdentityResult ValidateCandidate(string? password, string? email, string appName)
    {
        if (!HasAllowedCodePoints(password))
        {
            return Failure("PasswordLengthOrUnicode", "Use 15–128 Unicode characters without control characters.");
        }
        if (CommonPasswords.Value.Contains(password!)
            || string.Equals(password, email, StringComparison.OrdinalIgnoreCase)
            || string.Equals(password, appName, StringComparison.OrdinalIgnoreCase))
        {
            return Failure("PasswordTooCommon", "Choose a less common password, different from the application name and email address.");
        }
        return IdentityResult.Success;
    }

    private static bool HasAllowedCodePoints(string? password)
    {
        if (password is null || password.Length > 256) return false;
        var remaining = password.AsSpan();
        var count = 0;
        while (!remaining.IsEmpty)
        {
            if (Rune.DecodeFromUtf16(remaining, out var rune, out var consumed) != OperationStatus.Done || Rune.IsControl(rune))
            {
                return false;
            }
            count++;
            if (count > 128) return false;
            remaining = remaining[consumed..];
        }
        return count >= 15;
    }

    private static IdentityResult Failure(string code, string description) =>
        IdentityResult.Failed(new IdentityError { Code = code, Description = description });

    private static FrozenSet<string> LoadCommonPasswords()
    {
        const int maximumBytes = 256 * 1024;
        using var stream = typeof(AccountPasswordValidator).Assembly.GetManifestResourceStream(ResourceName)
            ?? throw new InvalidOperationException("The offline password resource is missing.");
        using var content = new MemoryStream();
        var buffer = new byte[4096];
        int read;
        while ((read = stream.Read(buffer)) > 0)
        {
            if (content.Length + read > maximumBytes)
            {
                throw new InvalidOperationException("The offline password resource exceeds its size limit.");
            }
            content.Write(buffer, 0, read);
        }
        var bytes = content.ToArray();
        if (!string.Equals(Convert.ToHexStringLower(SHA256.HashData(bytes)), ResourceSha256, StringComparison.Ordinal))
        {
            throw new InvalidOperationException("The offline password resource failed integrity verification.");
        }
        return Encoding.UTF8.GetString(bytes).Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries)
            .ToFrozenSet(StringComparer.OrdinalIgnoreCase);
    }
}
