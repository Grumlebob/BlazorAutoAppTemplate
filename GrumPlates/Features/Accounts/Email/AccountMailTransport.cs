using System.Net.Security;
using MailKit.Net.Smtp;
using MailKit.Security;
using Microsoft.Extensions.Options;
using MimeKit;

namespace GrumPlates.Features.Accounts.Email;

internal sealed class AccountMailTransportOptions
{
    // Only test composition sets this callback to trust its private loopback CA.
    public RemoteCertificateValidationCallback? ServerCertificateValidationCallback { get; set; }
}

internal sealed class MailKitAccountMailTransport(
    AccountOptions options,
    IOptions<AccountMailTransportOptions> transportOptions) : IAccountMailTransport
{
    public async Task SendAsync(AccountMailMessage mail, CancellationToken cancellationToken)
    {
        if (!options.EmailEnabled)
        {
            throw new InvalidOperationException("Account email delivery is disabled.");
        }

        var message = new MimeMessage { MessageId = mail.MessageId, Subject = mail.Subject };
        message.From.Add(MailboxAddress.Parse(options.Email.From));
        message.To.Add(MailboxAddress.Parse(mail.Recipient));
        message.Body = new TextPart("plain") { Text = mail.Text };

        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(15));
        using var smtp = new SmtpClient { Timeout = 15000 };
        if (transportOptions.Value.ServerCertificateValidationCallback is { } callback)
        {
            smtp.ServerCertificateValidationCallback = callback;
        }

        var security = options.Email.Security == "SslOnConnect"
            ? SecureSocketOptions.SslOnConnect
            : SecureSocketOptions.StartTls;
        await smtp.ConnectAsync(options.Email.Host, options.Email.Port, security, timeout.Token);

        if (!string.IsNullOrEmpty(options.Email.Username))
        {
            await smtp.AuthenticateAsync(options.Email.Username, options.Email.Password, timeout.Token);
        }

        await smtp.SendAsync(message, timeout.Token);
        await smtp.DisconnectAsync(true, timeout.Token);
    }
}
