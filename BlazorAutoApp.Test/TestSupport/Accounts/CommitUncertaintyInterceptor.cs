using System.Data.Common;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Npgsql;

namespace BlazorAutoApp.Test.TestSupport.Accounts;

internal sealed class CommitUncertaintyInterceptor : DbTransactionInterceptor
{
    private int _armed;
    private int _thrown;

    public int ThrownCount => Volatile.Read(ref _thrown);

    public void ThrowAfterNextCommit() => Interlocked.Exchange(ref _armed, 1);

    public override Task TransactionCommittedAsync(
        DbTransaction transaction,
        TransactionEndEventData eventData,
        CancellationToken cancellationToken = default)
    {
        if (Interlocked.Exchange(ref _armed, 0) == 1)
        {
            Interlocked.Increment(ref _thrown);
            throw new PostgresException("Synthetic lost commit acknowledgement.", "ERROR", "ERROR", "40001");
        }

        return Task.CompletedTask;
    }
}
