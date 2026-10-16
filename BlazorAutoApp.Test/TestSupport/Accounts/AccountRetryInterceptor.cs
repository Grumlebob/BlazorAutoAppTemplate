using System.Data.Common;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Npgsql;

namespace BlazorAutoApp.Test.TestSupport.Accounts;

internal sealed class AccountRetryInterceptor : DbTransactionInterceptor
{
    private Func<Task>? _afterRollback;
    public int RetriedCount { get; private set; }

    public void RollBackNextCommit(Func<Task> afterRollback) => _afterRollback = afterRollback;

    public override async ValueTask<InterceptionResult> TransactionCommittingAsync(
        DbTransaction transaction,
        TransactionEventData eventData,
        InterceptionResult result,
        CancellationToken cancellationToken = default)
    {
        var afterRollback = Interlocked.Exchange(ref _afterRollback, null);
        if (afterRollback is not null)
        {
            await transaction.RollbackAsync(cancellationToken);
            await afterRollback();
            RetriedCount++;
            throw new PostgresException("Synthetic rolled-back account transaction.", "ERROR", "ERROR", "40001");
        }

        return result;
    }
}
