using BlazorAutoApp.Core.Features.Inspections.StartHullInspectionEmail;
using BlazorAutoApp.Core.Features.Email;

namespace BlazorAutoApp.Features.Inspections.StartHullInspectionEmail;

public class StartHullInspectionEmailServerService(AppDbContext db, IEmailApi email, ILogger<StartHullInspectionEmailServerService> log)
    : IStartHullInspectionEmailApi
{
    private readonly AppDbContext _db = db;
    private readonly IEmailApi _email = email;
    private readonly ILogger<StartHullInspectionEmailServerService> _log = log;

    public async Task<GetCompaniesResponse> GetCompaniesAsync(CancellationToken ct = default)
    {
        var items = await _db.CompanyDetails
            .AsNoTracking()
            .OrderBy(c => c.Id)
            .Select(c => new CompanyListItem { Id = c.Id, Name = c.Name })
            .ToListAsync(ct);
        return new GetCompaniesResponse { Items = items };
    }

    public async Task<StartHullInspectionResponse> StartAsync(StartHullInspectionRequest req, CancellationToken ct = default)
    {
        var company = await _db.CompanyDetails.FirstOrDefaultAsync(c => c.Id == req.CompanyId, ct);
        if (company is null)
        {
            return new StartHullInspectionResponse { Success = false, Error = "Company not found" };
        }

        try
        {
            company.HasActivatedLatestInspectionEmail = false;
            // Create a new Inspection with id + password
            var inspectionId = Guid.NewGuid();
            var password = BlazorAutoApp.Features.Inspections.VerifyInspectionEmail.InspectionServerService.GeneratePassword(10);
            var (salt, hash) = BlazorAutoApp.Features.Inspections.VerifyInspectionEmail.InspectionServerService.HashPassword(password);
            _db.Inspections.Add(new BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection
            {
                Id = inspectionId,
                CompanyId = company.Id,
                PasswordSalt = salt,
                PasswordHash = hash,
                CreatedAtUtc = DateTime.UtcNow
            });
            await _db.SaveChangesAsync(ct);
            var send = await _email.SendAsync(new SendEmailRequest
            {
                To = company.Email,
                Subject = "Start Hull Inspection",
                Text = $"Hello,\n\nAn inspection has been initiated.\n\nInspection ID: {inspectionId}\nPassword: {password}\n\nNavigate to /inspection/{inspectionId} and enter the password to proceed.\n"
            }, ct);

            return new StartHullInspectionResponse { Success = send.Success, Error = send.Error };
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Failed to send hull inspection email to Company {Id}", company.Id);
            return new StartHullInspectionResponse { Success = false, Error = ex.Message };
        }
    }
}
