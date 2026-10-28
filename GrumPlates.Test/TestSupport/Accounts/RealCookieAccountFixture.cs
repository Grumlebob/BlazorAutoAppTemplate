using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using GrumPlates.Core.Features.Accounts.Contracts;
using GrumPlates.Features.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;

namespace GrumPlates.Test.TestSupport.Accounts;

internal sealed class RealCookieAccountFixture : IAsyncDisposable
{
    private readonly DirectoryInfo _keys = Directory.CreateTempSubdirectory("GrumPlates-account-keys-");
    private const string KeyCertificatePassword = "account-fixture-key-password";
    public string KeyEncryptionCertificatePath { get; }
    public AccountTestClock Clock { get; }
    public WebAppFactory Factory { get; }

    public RealCookieAccountFixture(
        IReadOnlyDictionary<string, string?>? configurationOverrides = null,
        Action<IServiceCollection>? configureTestServices = null,
        string? appName = null,
        string? postgresConnectionString = null,
        AccountTestClock? clock = null,
        string? redisConnectionString = null,
        bool runMigrationsAtStartup = true,
        string? keyEncryptionCertificatePath = null)
    {
        Clock = clock ?? new AccountTestClock();
        var certificatePath = keyEncryptionCertificatePath ?? Path.Combine(_keys.FullName, "data-protection.pfx");
        if (keyEncryptionCertificatePath is null)
        {
            using var rsa = RSA.Create(2048);
            using var certificate = new CertificateRequest(
                    $"CN=GrumPlates account fixture {Guid.NewGuid():N}",
                    rsa,
                    HashAlgorithmName.SHA256,
                    RSASignaturePadding.Pkcs1)
                .CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1), DateTimeOffset.UtcNow.AddYears(5));
            File.WriteAllBytes(certificatePath, certificate.Export(X509ContentType.Pfx, KeyCertificatePassword));
        }
        KeyEncryptionCertificatePath = certificatePath;

        var accountConfiguration = new Dictionary<string, string?>
        {
            ["Accounts:Enabled"] = "true",
            ["Accounts:RegistrationEnabled"] = "false",
            ["Accounts:AdminSeed:Enabled"] = "false",
            ["Accounts:Email:Host"] = "",
            ["DataProtection:KeyStoragePath"] = _keys.FullName,
            ["DataProtection:KeyEncryptionCertificatePath"] = certificatePath,
            ["DataProtection:KeyEncryptionCertificatePassword"] = KeyCertificatePassword
        };
        if (configurationOverrides is not null)
        {
            foreach (var (key, value) in configurationOverrides)
            {
                accountConfiguration[key] = value;
            }
        }

        Factory = new WebAppFactory(new WebAppFactoryOptions
        {
            UseRealIdentityCookies = true,
            InitializeDatabaseRespawner = false,
            AppName = appName ?? $"account-cookies-{Guid.NewGuid():N}",
            PostgresConnectionString = postgresConnectionString,
            RedisConnectionString = redisConnectionString,
            RunMigrationsAtStartup = runMigrationsAtStartup,
            EnvironmentName = "Testing",
            ConfigurationOverrides = accountConfiguration,
            ConfigureTestServices = services =>
            {
                services.AddSingleton<TimeProvider>(Clock);
                services.PostConfigure<CookieAuthenticationOptions>(IdentityConstants.ApplicationScheme, options => options.TimeProvider = Clock);
                services.Configure<SecurityStampValidatorOptions>(options => options.TimeProvider = Clock);
                configureTestServices?.Invoke(services);
            }
        });
    }

    public Task InitializeAsync() => Factory.InitializeAsync().AsTask();

    public HttpClient CreateClient() => Factory.CreateClient(new WebApplicationFactoryClientOptions
    {
        BaseAddress = new Uri("https://localhost"),
        AllowAutoRedirect = false,
        HandleCookies = true
    });

    public async Task<(string Id, string Email, string Password)> CreateUserAsync(bool confirmed = true)
    {
        using var scope = Factory.Services.CreateScope();
        var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var email = $"{Guid.NewGuid():N}@example.test";
        var password = RandomNumberGenerator.GetHexString(48);
        var user = new ApplicationUser { Email = email, UserName = email, EmailConfirmed = confirmed };
        var created = await users.CreateAsync(user, password);
        if (!created.Succeeded) throw new InvalidOperationException("Generated fixture account could not be created.");
        return (user.Id, email, password);
    }

    public static async Task<AccountSession> ReadSessionAsync(HttpClient client) =>
        await client.GetFromJsonAsync<AccountSession>("/api/auth/session")
        ?? throw new InvalidOperationException("Fixture session response was missing.");

    public static async Task<HttpResponseMessage> LoginAsync(HttpClient client, string email, string password, bool rememberMe = false)
    {
        var session = await ReadSessionAsync(client);
        using var request = new HttpRequestMessage(HttpMethod.Post, "/api/auth/login")
        {
            Content = JsonContent.Create(new { email, password, rememberMe })
        };
        request.Headers.Add("X-CSRF-TOKEN", session.CsrfToken);
        return await client.SendAsync(request);
    }

    public async ValueTask DisposeAsync()
    {
        await Factory.DisposeAsync();
        // This exact directory was created by this fixture and never shared.
        _keys.Delete(recursive: true);
    }
}

internal sealed class AccountTestClock : TimeProvider
{
    private DateTimeOffset _utcNow = DateTimeOffset.FromUnixTimeSeconds(DateTimeOffset.UtcNow.ToUnixTimeSeconds());
    public override DateTimeOffset GetUtcNow() => _utcNow;
    public void Advance(TimeSpan duration) => _utcNow = _utcNow.Add(duration);
}
