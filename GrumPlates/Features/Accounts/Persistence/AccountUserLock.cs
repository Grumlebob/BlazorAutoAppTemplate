using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;

namespace GrumPlates.Features.Accounts.Persistence;

internal static class AccountUserLock
{
    // The caller owns the transaction. Reload only after acquiring the row lock so
    // credential and stamp checks observe the account state protected by that lock.
    public static async Task<bool> TryLockAndReloadAsync(
        AppDbContext db, ApplicationUser user, CancellationToken cancellationToken)
    {
        await using var command = db.Database.GetDbConnection().CreateCommand();
        command.Transaction = db.Database.CurrentTransaction?.GetDbTransaction()
            ?? throw new InvalidOperationException("Account row locking requires an active transaction.");
        command.CommandText = "SELECT 1 FROM \"AspNetUsers\" WHERE \"Id\" = @userId FOR UPDATE";
        var parameter = command.CreateParameter();
        parameter.ParameterName = "userId";
        parameter.Value = user.Id;
        command.Parameters.Add(parameter);
        await using (var reader = await command.ExecuteReaderAsync(cancellationToken))
        {
            if (!await reader.ReadAsync(cancellationToken)) return false;
        }

        await db.Entry(user).ReloadAsync(cancellationToken);
        return true;
    }
}
