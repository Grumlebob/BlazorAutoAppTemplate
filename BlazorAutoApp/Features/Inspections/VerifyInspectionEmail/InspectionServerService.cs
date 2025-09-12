using System.Security.Cryptography;
using System.Text;
using BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail;

namespace BlazorAutoApp.Features.Inspections.VerifyInspectionEmail;

public class InspectionServerService(AppDbContext db, ILogger<InspectionServerService> log) : IInspectionApi
{
    private readonly AppDbContext _db = db;
    private readonly ILogger<InspectionServerService> _log = log;

    public async Task<VerifyInspectionPasswordResponse> VerifyPasswordAsync(VerifyInspectionPasswordRequest req, CancellationToken ct = default)
    {
        var item = await _db.Set<BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection>()
            .FirstOrDefaultAsync(i => i.Id == req.Id, ct);
        if (item is null)
            return new VerifyInspectionPasswordResponse { Success = false, Error = "Inspection not found" };

        var ok = VerifyPassword(req.Password, item.PasswordSalt, item.PasswordHash);
        if (ok)
        {
            item.VerifiedAtUtc = DateTime.UtcNow;
            // flip company flag to true
            var company = await _db.CompanyDetails.FirstOrDefaultAsync(c => c.Id == item.CompanyId, ct);
            if (company is not null)
            {
                company.HasActivatedLatestInspectionEmail = true;
            }
            await _db.SaveChangesAsync(ct);
        }
        return new VerifyInspectionPasswordResponse { Success = ok, Error = ok ? null : "Invalid password" };
    }

    public async Task<InspectionStatusResponse> GetStatusAsync(Guid id, CancellationToken ct = default)
    {
        var item = await _db.Set<BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection>()
            .AsNoTracking()
            .FirstOrDefaultAsync(x => x.Id == id, ct);
        if (item is null)
            return new InspectionStatusResponse { Verified = false, CompanyId = 0 };
        return new InspectionStatusResponse { Verified = item.VerifiedAtUtc != null, CompanyId = item.CompanyId };
    }

    public static string GeneratePassword(int length = 10)
    {
        const string chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
        var bytes = RandomNumberGenerator.GetBytes(length);
        var sb = new StringBuilder(length);
        foreach (var b in bytes)
            sb.Append(chars[b % chars.Length]);
        return sb.ToString();
    }

    public static (string Salt, string Hash) HashPassword(string password)
    {
        var saltBytes = RandomNumberGenerator.GetBytes(16);
        var salt = Convert.ToBase64String(saltBytes);
        using var sha = SHA256.Create();
        var combined = Encoding.UTF8.GetBytes(password + ":" + salt);
        var hash = Convert.ToBase64String(sha.ComputeHash(combined));
        return (salt, hash);
    }

    public static bool VerifyPassword(string password, string salt, string expectedHash)
    {
        using var sha = SHA256.Create();
        var combined = Encoding.UTF8.GetBytes(password + ":" + salt);
        var hash = Convert.ToBase64String(sha.ComputeHash(combined));
        return CryptographicOperations.FixedTimeEquals(Convert.FromBase64String(hash), Convert.FromBase64String(expectedHash));
    }
}
