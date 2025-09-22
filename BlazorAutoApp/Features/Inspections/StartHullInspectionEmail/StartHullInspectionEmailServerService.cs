using BlazorAutoApp.Core.Features.Inspections.StartHullInspectionEmail;
using BlazorAutoApp.Core.Features.Email;

namespace BlazorAutoApp.Features.Inspections.StartHullInspectionEmail;

public class StartHullInspectionEmailServerService(AppDbContext db, IEmailApi email, ILogger<StartHullInspectionEmailServerService> log, IConfiguration cfg)
    : IStartHullInspectionEmailApi
{
    private readonly AppDbContext _db = db;
    private readonly IEmailApi _email = email;
    private readonly ILogger<StartHullInspectionEmailServerService> _log = log;
    private readonly IConfiguration _cfg = cfg;

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
            // Create a new Inspection with id only (passwordless)
            var inspectionId = Guid.NewGuid();
            _db.Inspections.Add(new BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection
            {
                Id = inspectionId,
                CompanyId = company.Id,
                CreatedAtUtc = DateTime.UtcNow
            });
            await _db.SaveChangesAsync(ct);
            var baseUrl = _cfg["App:Url"] ?? string.Empty;
            var link = new Uri(new Uri(baseUrl, UriKind.Absolute), $"/inspection/{inspectionId}/flow").ToString();

            var toEmail = string.IsNullOrWhiteSpace(req.RecipientEmail) ? company.Email : req.RecipientEmail;
            var helloName = string.IsNullOrWhiteSpace(req.RecipientName) ? null : req.RecipientName;

            var send = await _email.SendAsync(new SendEmailRequest
            {
                To = toEmail,
                Subject = "Start Hull Inspection",
                Text = $"Hello{(helloName is null ? string.Empty : " " + helloName)},\n\nAn inspection has been initiated.\n\nInspection ID: {inspectionId}\n\nOpen the inspection flow directly at: {link} \n",
                Html = $"<p>Hello{(helloName is null ? string.Empty : " " + System.Net.WebUtility.HtmlEncode(helloName))},</p><p>An inspection has been initiated.</p><p><strong>Inspection ID:</strong> {inspectionId}</p><p><a href=\"{link}\">Open the inspection flow</a></p>"
            }, ct);

            return new StartHullInspectionResponse { Success = send.Success, Error = send.Error };
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Failed to send hull inspection email to Company {Id}", company.Id);
            return new StartHullInspectionResponse { Success = false, Error = ex.Message };
        }
    }

    public async Task<ActivateInspectionResponse> ActivateAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            var insp = await _db.Inspections.AsNoTracking().FirstOrDefaultAsync(i => i.Id == id, ct);
            if (insp is null)
                return new ActivateInspectionResponse { Success = false, Error = "Inspection not found" };

            var company = await _db.CompanyDetails.FirstOrDefaultAsync(c => c.Id == insp.CompanyId, ct);
            if (company is null)
                return new ActivateInspectionResponse { Success = false, Error = "Company not found" };

            if (!company.HasActivatedLatestInspectionEmail)
            {
                company.HasActivatedLatestInspectionEmail = true;
                await _db.SaveChangesAsync(ct);
            }
            return new ActivateInspectionResponse { Success = true };
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Activation failed for inspection {Id}", id);
            return new ActivateInspectionResponse { Success = false, Error = ex.Message };
        }
    }
}
