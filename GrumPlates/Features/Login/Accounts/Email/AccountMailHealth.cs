using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace GrumPlates.Features.Login.Accounts.Email;

internal sealed class AccountMailHealth
{
    private readonly object _gate = new();
    private string? _lastFailureCode;
    private DateTimeOffset? _lastFailureUtc;
    private long _sent;
    private long _retried;
    private long _failed;

    public void Sent()
    {
        Interlocked.Increment(ref _sent);
        lock (_gate)
        {
            _lastFailureCode = null;
            _lastFailureUtc = null;
        }
    }

    public void Retried() => Interlocked.Increment(ref _retried);

    public void Failed(string failureCode, DateTimeOffset at)
    {
        Interlocked.Increment(ref _failed);
        lock (_gate)
        {
            _lastFailureCode = failureCode;
            _lastFailureUtc = at;
        }
    }

    public (string? FailureCode, DateTimeOffset? FailureUtc, long Sent, long Retried, long Failed) Snapshot()
    {
        lock (_gate)
        {
            return (_lastFailureCode, _lastFailureUtc,
                Interlocked.Read(ref _sent), Interlocked.Read(ref _retried), Interlocked.Read(ref _failed));
        }
    }
}

internal sealed class AccountMailHealthCheck(AccountMailHealth health) : IHealthCheck
{
    public Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, CancellationToken cancellationToken = default)
    {
        var snapshot = health.Snapshot();
        var data = new Dictionary<string, object>
        {
            ["sent"] = snapshot.Sent,
            ["retried"] = snapshot.Retried,
            ["failed"] = snapshot.Failed
        };
        if (snapshot.FailureCode is not null)
        {
            data["lastFailureCode"] = snapshot.FailureCode;
            data["lastFailureUtc"] = snapshot.FailureUtc?.ToString("O") ?? "";
            return Task.FromResult(HealthCheckResult.Degraded("Account email delivery has a recorded failure.", data: data));
        }

        return Task.FromResult(HealthCheckResult.Healthy("No account email delivery failure is recorded.", data));
    }
}
