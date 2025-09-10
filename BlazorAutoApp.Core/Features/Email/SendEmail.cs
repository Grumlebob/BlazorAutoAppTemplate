namespace BlazorAutoApp.Core.Features.Email;

public class SendEmailRequest
{
    public required string To { get; set; }
    public string? Subject { get; set; }
    public string? Text { get; set; }
    public string? Html { get; set; }
}

public class SendEmailResponse
{
    public bool Success { get; set; }
    public string? Error { get; set; }
}

public interface IEmailApi
{
    Task<SendEmailResponse> SendAsync(SendEmailRequest req, CancellationToken ct = default);
}

