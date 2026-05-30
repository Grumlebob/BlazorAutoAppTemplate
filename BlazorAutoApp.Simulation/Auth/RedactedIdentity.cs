using System.Security.Cryptography;
using System.Text;

namespace BlazorAutoApp.Simulation.Auth;

internal static class RedactedIdentity
{
    public static string HashEmail(string email)
    {
        var normalized = email.Trim().ToUpperInvariant();
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(normalized));
        return Convert.ToHexString(bytes)[..12].ToLowerInvariant();
    }
}
