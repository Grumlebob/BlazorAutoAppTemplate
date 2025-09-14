using BlazorAutoApp.Core.Features.Email;
using SendGrid;
using SendGrid.Helpers.Mail;

namespace BlazorAutoApp.Features.Email;

public class EmailServerService(IConfiguration cfg, ILogger<EmailServerService> log) : IEmailApi
{
    public async Task<SendEmailResponse> SendAsync(SendEmailRequest req, CancellationToken ct = default)
    {
        // Resolve API key (env var takes precedence, then config section)
        var apiKey = Environment.GetEnvironmentVariable("SENDGRID_API_KEY")
                     ?? cfg["SENDGRID_API_KEY"]
                     ?? cfg["SendGrid:ApiKey"];
        if (string.IsNullOrWhiteSpace(apiKey))
        {
            return new SendEmailResponse { Success = false, Error = "SendGrid ApiKey not configured" };
        }


        // Data residency: only set if configured. If not provided, SDK uses US region.
        var dataResidency = Environment.GetEnvironmentVariable("SENDGRID_DATA_RESIDENCY")
                             ?? cfg["SENDGRID_DATA_RESIDENCY"]
                             ?? cfg["SendGrid:DataResidency"];

        try
        {
            var options = new SendGridClientOptions
            {
                ApiKey = apiKey
            };
            if (!string.IsNullOrWhiteSpace(dataResidency))
            {
                options.SetDataResidency(dataResidency);
            }
            var client = new SendGridClient(options);

            var fromEmail = new EmailAddress("shampoo148@live.dk", "Grumbo");
            var to = new EmailAddress("grumlebet@gmail.com", "Grumbo");
            var subject = req.Subject ?? string.Empty;
            var plainTextContent = req.Text;
            var htmlContent = req.Html;
            var msg = MailHelper.CreateSingleEmail(fromEmail, to, subject, plainTextContent, htmlContent);
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
