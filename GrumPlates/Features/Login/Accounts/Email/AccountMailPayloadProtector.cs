using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;

namespace GrumPlates.Features.Login.Accounts.Email;

internal sealed class AccountMailPayloadProtector
{
    private const string Purpose = "GrumPlates.AccountMailOutbox.v1";
    private readonly IDataProtector _protector;

    public AccountMailPayloadProtector(IDataProtectionProvider provider)
    {
        _protector = provider.CreateProtector(Purpose);
    }

    public string Protect(AccountMailPayload payload) =>
        _protector.Protect(JsonSerializer.Serialize(payload));

    public AccountMailPayload Unprotect(string protectedPayload)
    {
        var json = _protector.Unprotect(protectedPayload);
        return JsonSerializer.Deserialize<AccountMailPayload>(json)
            ?? throw new CryptographicException("Protected account mail payload is empty.");
    }
}
