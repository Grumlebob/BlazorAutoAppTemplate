using BlazorAutoApp.Core.Features.Email;
using SendGrid;
using SendGrid.Helpers.Mail;

namespace BlazorAutoApp.Features.Email;

public class EmailServerService(IConfiguration cfg, ILogger<EmailServerService> log) : IEmailApi
{
    public async Task<SendEmailResponse> SendAsync(SendEmailRequest req, CancellationToken ct = default)
    {
        // Resolve from configuration only; Program.cs maps env vars into configuration
        var apiKey = cfg["SendGrid:ApiKey"];
        if (string.IsNullOrWhiteSpace(apiKey))
        {
            return new SendEmailResponse { Success = false, Error = "SendGrid ApiKey not configured" };
        }
        
        var fromEmail = cfg["SendGrid:FromEmail"];
        if (string.IsNullOrWhiteSpace(fromEmail))
        {
            return new SendEmailResponse { Success = false, Error = "SendGrid FromEmail not configured" };
        }

        var fromAlias = cfg["SendGrid:FromAlias"];
        if (string.IsNullOrWhiteSpace(fromAlias))
        {
            return new SendEmailResponse { Success = false, Error = "SendGrid fromAlias not configured" };
        }
        try
        {
            var options = new SendGridClientOptions
            {
                ApiKey = apiKey
            };
            var client = new SendGridClient(options);
            
            var to = new EmailAddress(req.To, "Grumbo");
            var subject = req.Subject ?? string.Empty;
            var plainTextContent = req.Text;
            var htmlContent = req.Html;
            var msg = MailHelper.CreateSingleEmail(new EmailAddress(fromEmail, fromAlias), to, subject, plainTextContent, htmlContent);
            var response = await client.SendEmailAsync(msg);
            if ((int)response.StatusCode == 202)
                return new SendEmailResponse { Success = true };
            log.LogWarning("SendGrid send failed: {Status}", (int)response.StatusCode);
            var bodyText = await response.Body.ReadAsStringAsync();
            return new SendEmailResponse { Success = false, Error = "SendGrid " + ((int)response.StatusCode).ToString() + "and" + bodyText };
        }
        catch (Exception ex)
        {
            log.LogError(ex, "SendGrid exception");
            return new SendEmailResponse { Success = false, Error = ex.Message };
        }
    }
}
