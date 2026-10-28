using System.Net;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using MailKit.Net.Smtp;
using MailKit.Security;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using MimeKit;
using Xunit;

namespace GrumPlates.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountFixtureTests
{
    [Fact]
    public async Task RealIdentityFixture_AnonymousAndSpoofedPrincipalAreDenied()
    {
        await using var factory = new WebAppFactory(new WebAppFactoryOptions
        {
            UseRealIdentityCookies = true,
            InitializeDatabaseRespawner = false,
            AppName = $"accounts-fixture-{Guid.NewGuid():N}",
            ConfigurationOverrides = new() { ["Accounts:Enabled"] = "false" }
        });
        await factory.InitializeAsync();
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            BaseAddress = new Uri("https://localhost"),
            AllowAutoRedirect = false,
            HandleCookies = true
        });
        var schemes = factory.Services.GetRequiredService<IAuthenticationSchemeProvider>();
        Assert.Equal(IdentityConstants.ApplicationScheme, (await schemes.GetDefaultAuthenticateSchemeAsync())?.Name);
        Assert.Null(await schemes.GetSchemeAsync(TestAuthenticationHandler.SchemeName));
        Assert.Throws<InvalidOperationException>(() => factory.CreateAuthenticatedClient());

        using var anonymous = await client.GetAsync("/api/books");
        Assert.Equal(HttpStatusCode.Unauthorized, anonymous.StatusCode);
        Assert.Null(anonymous.Headers.Location);
        client.DefaultRequestHeaders.Add(TestAuthenticationHandler.UserHeader, "spoof@example.test");
        using var spoofed = await client.GetAsync("/api/books");
        Assert.Equal(HttpStatusCode.Unauthorized, spoofed.StatusCode);
    }

    [Fact]
    public async Task SmtpFixture_CapturesMessageOnlyOverTrustedStartTls()
    {
        await using var inbox = new TlsSmtpFixture();
        using var smtp = new SmtpClient { ServerCertificateValidationCallback = inbox.ValidateCertificate };
        await smtp.ConnectAsync("localhost", inbox.Port, SecureSocketOptions.StartTls);
        Assert.True(smtp.IsSecure);
        using var message = new MimeMessage();
        message.From.Add(MailboxAddress.Parse("sender@example.test"));
        message.To.Add(MailboxAddress.Parse($"{Guid.NewGuid():N}@example.test"));
        message.Subject = "Isolated account fixture";
        message.Body = new TextPart("plain") { Text = "Fixture capture; no external delivery.\r\n" };
        await smtp.SendAsync(message);
        await smtp.DisconnectAsync(true);
        using var received = await inbox.ReadMessageAsync();
        Assert.Equal(message.To.ToString(), received.To.ToString());
        Assert.Equal(message.TextBody, received.TextBody);
    }

    [Fact]
    public async Task SmtpFixture_RejectsUntrustedCertificate()
    {
        await using var inbox = new TlsSmtpFixture();
        using var smtp = new SmtpClient();
        await Assert.ThrowsAsync<SslHandshakeException>(() => smtp.ConnectAsync("localhost", inbox.Port, SecureSocketOptions.StartTls));
        Assert.False(smtp.IsConnected);
    }

    [Fact]
    public async Task SmtpFixture_RejectsAnUnrelatedFixtureCa()
    {
        await using var inbox = new TlsSmtpFixture();
        await using var unrelated = new TlsSmtpFixture();
        using var smtp = new SmtpClient { ServerCertificateValidationCallback = unrelated.ValidateCertificate };
        await Assert.ThrowsAsync<SslHandshakeException>(() => smtp.ConnectAsync("localhost", inbox.Port, SecureSocketOptions.StartTls));
        Assert.False(smtp.IsConnected);
    }

    [Fact]
    public async Task SmtpFixture_RefusesPlaintextMail()
    {
        await using var inbox = new TlsSmtpFixture();
        using var smtp = new SmtpClient();
        await smtp.ConnectAsync("localhost", inbox.Port, SecureSocketOptions.None);
        using var message = new MimeMessage();
        message.From.Add(MailboxAddress.Parse("sender@example.test"));
        message.To.Add(MailboxAddress.Parse("recipient@example.test"));
        message.Body = new TextPart("plain") { Text = "Must not be accepted without TLS." };
        var error = await Assert.ThrowsAsync<MailKit.ServiceNotAuthenticatedException>(() => smtp.SendAsync(message));
        Assert.Equal("STARTTLS required", error.Message);
        await smtp.DisconnectAsync(true);
    }
}
