using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading.Channels;
using MimeKit;

namespace GrumPlates.Test.TestSupport.Accounts;

/// <summary>A loopback-only STARTTLS inbox. It never relays mail or changes machine trust.</summary>
internal sealed class TlsSmtpFixture : IAsyncDisposable
{
    private readonly TcpListener _listener = new(IPAddress.Loopback, 0);
    private readonly CancellationTokenSource _stop = new();
    private readonly X509Certificate2 _serverCertificate;
    private readonly Channel<MimeMessage> _messages = Channel.CreateBounded<MimeMessage>(100);
    private readonly Task _server;
    private readonly List<Task> _connections = [];

    public X509Certificate2 RootCertificate { get; }
    public int Port => ((IPEndPoint)_listener.LocalEndpoint).Port;

    public TlsSmtpFixture()
    {
        var now = DateTimeOffset.UtcNow;
        using var rootKey = RSA.Create(2048);
        var rootRequest = new CertificateRequest("CN=Account fixture CA", rootKey, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        rootRequest.CertificateExtensions.Add(new X509BasicConstraintsExtension(true, false, 0, true));
        rootRequest.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.KeyCertSign, true));
        using var root = rootRequest.CreateSelfSigned(now.AddMinutes(-5), now.AddDays(1));
        RootCertificate = X509CertificateLoader.LoadCertificate(root.RawData);

        using var serverKey = RSA.Create(2048);
        var request = new CertificateRequest("CN=localhost", serverKey, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false, false, 0, true));
        request.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature | X509KeyUsageFlags.KeyEncipherment, true));
        request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(new OidCollection { new("1.3.6.1.5.5.7.3.1") }, true));
        var names = new SubjectAlternativeNameBuilder();
        names.AddDnsName("localhost");
        names.AddIpAddress(IPAddress.Loopback);
        request.CertificateExtensions.Add(names.Build());
        using var signed = request.Create(root, now.AddMinutes(-4), now.AddHours(12), RandomNumberGenerator.GetBytes(16));
        using var withPrivateKey = signed.CopyWithPrivateKey(serverKey);
        // Schannel requires a provider-backed key rather than CopyWithPrivateKey's
        // transient handle. Import only into the current process; never machine trust.
        _serverCertificate = X509CertificateLoader.LoadPkcs12(withPrivateKey.Export(X509ContentType.Pkcs12), null);
        _listener.Start();
        _server = AcceptAsync();
    }

    // Tests inject this callback into their client only. Hostname validation still
    // applies, and an unrelated CA cannot satisfy the custom trust chain.
    public bool ValidateCertificate(object sender, X509Certificate? certificate, X509Chain? chain, SslPolicyErrors errors)
    {
        if (certificate is null || (errors & ~SslPolicyErrors.RemoteCertificateChainErrors) != SslPolicyErrors.None)
        {
            return false;
        }

        using var customChain = new X509Chain();
        customChain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        customChain.ChainPolicy.CustomTrustStore.Add(RootCertificate);
        customChain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        customChain.ChainPolicy.ApplicationPolicy.Add(new Oid("1.3.6.1.5.5.7.3.1"));
        using var leaf = X509CertificateLoader.LoadCertificate(certificate.GetRawCertData());
        return customChain.Build(leaf);
    }

    public async Task<MimeMessage> ReadMessageAsync(CancellationToken cancellationToken = default) =>
        await _messages.Reader.ReadAsync(cancellationToken).AsTask().WaitAsync(TimeSpan.FromSeconds(15), cancellationToken);

    private async Task AcceptAsync()
    {
        try
        {
            while (!_stop.IsCancellationRequested)
            {
                var client = await _listener.AcceptTcpClientAsync(_stop.Token);
                _connections.Add(ServeAsync(client));
            }
        }
        catch (OperationCanceledException) when (_stop.IsCancellationRequested) { }
    }

    private async Task ServeAsync(TcpClient client)
    {
        using (client)
        using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(_stop.Token))
        {
            timeout.CancelAfter(TimeSpan.FromSeconds(30));
            var cancellationToken = timeout.Token;
            Stream stream = client.GetStream();
            SslStream? tls = null;
            var reader = NewReader(stream);
            var writer = NewWriter(stream);
            try
            {
                await writer.WriteLineAsync("220 localhost fixture ready".AsMemory(), cancellationToken);
                while (await reader.ReadLineAsync(cancellationToken) is { } command)
                {
                    if (command.Length > 4096) throw new IOException("SMTP fixture command limit exceeded.");
                    var verb = command.Split(' ', 2)[0].ToUpperInvariant();
                    switch (verb)
                    {
                        case "EHLO":
                        case "HELO":
                            await writer.WriteLineAsync((tls is null ? "250-localhost\r\n250 STARTTLS" : "250 localhost").AsMemory(), cancellationToken);
                            break;
                        case "STARTTLS" when tls is null:
                            await writer.WriteLineAsync("220 Begin TLS".AsMemory(), cancellationToken);
                            reader.Dispose();
                            writer.Dispose();
                            tls = new SslStream(stream, leaveInnerStreamOpen: true);
                            await tls.AuthenticateAsServerAsync(new SslServerAuthenticationOptions
                            {
                                ServerCertificate = _serverCertificate,
                                EnabledSslProtocols = SslProtocols.Tls12 | SslProtocols.Tls13
                            }, cancellationToken);
                            reader = NewReader(tls);
                            writer = NewWriter(tls);
                            break;
                        case "MAIL" when tls is not null:
                        case "RCPT" when tls is not null:
                        case "RSET":
                        case "NOOP":
                            await writer.WriteLineAsync("250 OK".AsMemory(), cancellationToken);
                            break;
                        case "DATA" when tls is not null:
                            await writer.WriteLineAsync("354 End with a dot".AsMemory(), cancellationToken);
                            var body = new StringBuilder();
                            while (await reader.ReadLineAsync(cancellationToken) is { } line && line != ".")
                            {
                                body.Append(line.StartsWith("..", StringComparison.Ordinal) ? line[1..] : line).Append("\r\n");
                                if (body.Length > 64 * 1024) throw new IOException("SMTP fixture message limit exceeded.");
                            }
                            using (var input = new MemoryStream(Encoding.UTF8.GetBytes(body.ToString())))
                            {
                                await _messages.Writer.WriteAsync(await MimeMessage.LoadAsync(input, cancellationToken), cancellationToken);
                            }
                            await writer.WriteLineAsync("250 Accepted".AsMemory(), cancellationToken);
                            break;
                        case "QUIT":
                            await writer.WriteLineAsync("221 Goodbye".AsMemory(), cancellationToken);
                            return;
                        default:
                            await writer.WriteLineAsync("530 STARTTLS required".AsMemory(), cancellationToken);
                            break;
                    }
                }
            }
            catch (AuthenticationException) { } // An untrusted-certificate test aborts the handshake.
            catch (IOException) { } // A rejecting client may close without QUIT.
            catch (OperationCanceledException) when (timeout.IsCancellationRequested) { }
            finally
            {
                reader.Dispose();
                writer.Dispose();
                if (tls is not null) await tls.DisposeAsync();
            }
        }
    }

    private static StreamReader NewReader(Stream stream) => new(stream, Encoding.UTF8, false, 1024, leaveOpen: true);
    private static StreamWriter NewWriter(Stream stream) => new(stream, new UTF8Encoding(false), 1024, leaveOpen: true)
    {
        NewLine = "\r\n",
        AutoFlush = true
    };

    public async ValueTask DisposeAsync()
    {
        await _stop.CancelAsync();
        _listener.Stop();
        await _server;
        await Task.WhenAll(_connections);
        _messages.Writer.TryComplete();
        _serverCertificate.Dispose();
        RootCertificate.Dispose();
        _stop.Dispose();
    }
}
