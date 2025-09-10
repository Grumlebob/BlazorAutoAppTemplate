using BlazorAutoApp.Core.Features.Email;
using SendGrid;
using SendGrid.Helpers.Mail;

namespace BlazorAutoApp.Features.Email;

public class EmailServerService(IConfiguration cfg, ILogger<EmailServerService> log) : IEmailApi
{
    private readonly IConfiguration _cfg = cfg;
    private readonly ILogger<EmailServerService> _log = log;

    public async Task<SendEmailResponse> SendAsync(SendEmailRequest req, CancellationToken ct = default)
    {
        var apiKey = _cfg["SendGrid:ApiKey"];
        var from = _cfg["SendGrid:FromEmail"] ?? _cfg["SendGrid:From"];
        if (string.IsNullOrWhiteSpace(apiKey) || string.IsNullOrWhiteSpace(from))
        {
            return new SendEmailResponse { Success = false, Error = "SendGrid ApiKey or FromEmail not configured" };
        }

        try
        {
            var sg = new SendGridClient(apiKey);
            var msg = new SendGridMessage();
            msg.SetFrom(new EmailAddress(from));
            msg.AddTo(new EmailAddress(req.To));
            msg.SetSubject(string.IsNullOrWhiteSpace(req.Subject) ? "Notification" : req.Subject);
            var anyContent = false;
            if (!string.IsNullOrWhiteSpace(req.Text)) { msg.AddContent("text/plain", req.Text); anyContent = true; }
            if (!string.IsNullOrWhiteSpace(req.Html)) { msg.AddContent("text/html", req.Html); anyContent = true; }
            if (!anyContent) { msg.AddContent("text/plain", string.Empty); }

            var res = await sg.SendEmailAsync(msg, ct);
            if ((int)res.StatusCode == 202)
                return new SendEmailResponse { Success = true };

            _log.LogWarning("SendGrid send failed: {Status}", (int)res.StatusCode);
            return new SendEmailResponse { Success = false, Error = $"SendGrid {(int)res.StatusCode}" };
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "SendGrid exception");
            return new SendEmailResponse { Success = false, Error = ex.Message };
        }
    }
}
