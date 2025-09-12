namespace BlazorAutoApp.Core.Features.Inspections.StartHullInspectionEmail;

// Entity mapped to table CompanyDetails (server config)
public class CompanyDetail
{
    public int Id { get; set; }
    public required string Name { get; set; }
    public required string Email { get; set; }
    public bool HasActivatedLatestInspectionEmail { get; set; }
}

// DTOs (do not expose Email to client)
public class CompanyListItem
{
    public int Id { get; set; }
    public required string Name { get; set; }
}

public class GetCompaniesResponse
{
    public List<CompanyListItem> Items { get; set; } = new();
}

public class StartHullInspectionRequest
{
    public required int CompanyId { get; set; }
}

public class StartHullInspectionResponse
{
    public bool Success { get; set; }
    public string? Error { get; set; }
}

public interface IStartHullInspectionEmailApi
{
    Task<GetCompaniesResponse> GetCompaniesAsync(CancellationToken ct = default);
    Task<StartHullInspectionResponse> StartAsync(StartHullInspectionRequest req, CancellationToken ct = default);
}
