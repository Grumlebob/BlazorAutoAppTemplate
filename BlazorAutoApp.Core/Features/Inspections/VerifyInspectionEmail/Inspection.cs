namespace BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail;

public class Inspection
{
    public Guid Id { get; set; }
    public int CompanyId { get; set; }
    public required string PasswordHash { get; set; }
    public required string PasswordSalt { get; set; }
    public DateTime CreatedAtUtc { get; set; }
    public DateTime? VerifiedAtUtc { get; set; }
}

public class VerifyInspectionPasswordRequest
{
    public required Guid Id { get; set; }
    public required string Password { get; set; }
}

public class VerifyInspectionPasswordResponse
{
    public bool Success { get; set; }
    public string? Error { get; set; }
}

public interface IVerifyInspectionEmailApi
{
    Task<VerifyInspectionPasswordResponse> VerifyPasswordAsync(VerifyInspectionPasswordRequest req, CancellationToken ct = default);
    Task<InspectionStatusResponse> GetStatusAsync(Guid id, CancellationToken ct = default);
}

public class InspectionStatusResponse
{
    public bool Verified { get; set; }
    public int CompanyId { get; set; }
}
