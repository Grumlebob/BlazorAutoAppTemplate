namespace GrumPlates.Features.Accounts.Persistence;

internal sealed class AccountOutboxMessage
{
    public Guid Id { get; set; }
    public string MessageId { get; set; } = "";
    public string UserId { get; set; } = "";
    public string Purpose { get; set; } = "";
    public string Status { get; set; } = "Pending";
    public string ProtectedPayload { get; set; } = "";
    public DateTimeOffset CreatedUtc { get; set; }
    public DateTimeOffset ExpiresUtc { get; set; }
    public DateTimeOffset NextAttemptUtc { get; set; }
    public int Attempts { get; set; }
    public string? LeaseId { get; set; }
    public DateTimeOffset? LeaseUntilUtc { get; set; }
    public string? FailureCode { get; set; }
}
