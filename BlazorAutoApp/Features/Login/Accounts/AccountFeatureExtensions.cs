using System.Net.Security;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using BlazorAutoApp.Features.Login.Accounts.Security;
using BlazorAutoApp.Features.Login.Accounts.Session;
using BlazorAutoApp.Features.Login.Accounts.Email;
using BlazorAutoApp.Features.Login.Account;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace BlazorAutoApp.Features.Login.Accounts;

internal static class AccountFeatureExtensions
{
    private const int MaximumJsonRequestBytes = 16 * 1024;
    private static readonly PathString[] UnsupportedIdentityPaths =
    [
        "/Account/ExternalLogin",
        "/Account/PerformExternalLogin",
        "/Account/LoginWith2fa",
        "/Account/LoginWithRecoveryCode",
        "/Account/PasskeyCreationOptions",
        "/Account/PasskeyRequestOptions",
        "/Account/Manage/ExternalLogins",
        "/Account/Manage/TwoFactorAuthentication",
        "/Account/Manage/EnableAuthenticator",
        "/Account/Manage/Disable2fa",
        "/Account/Manage/GenerateRecoveryCodes",
        "/Account/Manage/ResetAuthenticator",
        "/Account/Manage/Passkeys",
        "/Account/Manage/RenamePasskey"
    ];
    private static readonly HashSet<string> AccountJsonMutationPaths = new(StringComparer.OrdinalIgnoreCase)
    {
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/logout-all",
        "/api/auth/register",
        "/api/auth/resend-confirmation",
        "/api/auth/confirm-email",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/auth/change-password",
        "/api/auth/change-email",
        "/api/auth/confirm-email-change",
        "/api/auth/export",
        "/api/auth/delete"
    };

    public static IServiceCollection AddAccountFeature(this IServiceCollection services, IConfiguration configuration, IHostEnvironment environment)
    {
        var settings = configuration.GetSection("Accounts").Get<AccountOptions>() ?? new();
        var validation = new AccountOptionsValidator(configuration["App:Name"] ?? "BlazorAutoApp").Validate("Accounts", settings);
        if (validation.Failed)
        {
            throw new OptionsValidationException("Accounts", typeof(AccountOptions), validation.Failures);
        }
        services.AddSingleton(settings);
        services.AddSingleton<IOptions<AccountOptions>>(Options.Create(settings));
        var identity = new AccountApplicationIdentity(configuration["App:Name"] ?? "BlazorAutoApp", environment.EnvironmentName);
        services.AddSingleton(identity);
        services.AddOptions<AccountMailTransportOptions>();
        if (settings.EmailEnabled && environment.IsEnvironment("Docker")
            && configuration.GetValue<bool>("TestFixtures:Enabled"))
        {
            // The packaged SMTP fixture uses a private CA without a CRL. Keep this
            // strict custom-root trust path opt-in and limited to Docker test runs.
            var rootPath = configuration["TestFixtures:AccountSmtpRootCertificatePath"]
                ?? throw new InvalidOperationException("The SMTP test fixture root certificate path is required.");
            var rootCertificate = X509CertificateLoader.LoadCertificateFromFile(rootPath);
            services.AddSingleton(rootCertificate);
            services.Configure<AccountMailTransportOptions>(options =>
                options.ServerCertificateValidationCallback = (_, certificate, _, errors) =>
                    ValidateTestSmtpCertificate(rootCertificate, certificate, errors));
        }

        services.AddSingleton<AccountMailPayloadProtector>();
        services.AddSingleton<AccountEmailLinkFactory>();
        services.AddSingleton<AccountMailHealth>();
        services.AddSingleton<IAccountMailTransport, MailKitAccountMailTransport>();
        services.AddScoped<AccountMailOutbox>();
        services.AddScoped<AccountOperations>();
        services.AddScoped<AccountSessionOperations>();
        services.TryAddSingleton(TimeProvider.System);

        if (!settings.Enabled)
        {
            return services;
        }

        if (settings.EmailEnabled)
        {
            services.AddOptions<AccountMailWorkerSchedule>();
            services.AddHostedService<AccountMailOutboxWorker>();
            services.AddHealthChecks().AddCheck<AccountMailHealthCheck>("account-mail", tags: ["account-mail"]);
        }

        services.RemoveAll<IPasswordValidator<ApplicationUser>>();
        services.AddScoped<IPasswordValidator<ApplicationUser>, AccountPasswordValidator>();

        services.Configure<IdentityOptions>(options =>
        {
            options.User.RequireUniqueEmail = true;
            options.SignIn.RequireConfirmedEmail = true;
            // The shared validator counts Unicode code points, not UTF-16 units.
            options.Password.RequiredLength = 1;
            options.Password.RequiredUniqueChars = 1;
            options.Password.RequireDigit = false;
            options.Password.RequireUppercase = false;
            options.Password.RequireLowercase = false;
            options.Password.RequireNonAlphanumeric = false;
            options.Lockout.AllowedForNewUsers = true;
            options.Lockout.MaxFailedAccessAttempts = 5;
            options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(15);
        });
        services.Configure<DataProtectionTokenProviderOptions>(options => options.TokenLifespan = TimeSpan.FromHours(1));
        services.Configure<SecurityStampValidatorOptions>(options => options.ValidationInterval = TimeSpan.Zero);
        services.Configure<CookieAuthenticationOptions>(IdentityConstants.ApplicationScheme, options =>
        {
            options.Cookie.Name = $"__Host-Accounts-{identity.Id}";
            options.Cookie.Domain = null;
            options.Cookie.Path = "/";
            options.Cookie.HttpOnly = true;
            options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
            options.Cookie.SameSite = SameSiteMode.Lax;
            options.ExpireTimeSpan = TimeSpan.FromHours(8);
            options.SlidingExpiration = false;

            var defaultExpiry = options.ExpireTimeSpan;
            var existingSigningIn = options.Events.OnSigningIn;
            options.Events.OnSigningIn = async context =>
            {
                await existingSigningIn(context);
                if (context.Properties.IsPersistent
                    && context.Properties.IssuedUtc is { } issuedUtc
                    && context.Properties.ExpiresUtc == issuedUtc.Add(defaultExpiry))
                {
                    // The retained Blazor Identity forms set IsPersistent without an explicit expiry.
                    // Match the API's fixed 14-day remember-me ticket without extending explicit tickets.
                    context.Properties.ExpiresUtc = issuedUtc.AddDays(14);
                    context.Properties.AllowRefresh = false;
                }
            };
        });
        services.Configure<AntiforgeryOptions>(options =>
        {
            options.HeaderName = "X-CSRF-TOKEN";
            options.Cookie.Name = $"__Host-CSRF-{identity.Id}";
            options.Cookie.Domain = null;
            options.Cookie.Path = "/";
            options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
            options.Cookie.SameSite = SameSiteMode.Strict;
        });
        return services;
    }

    private static bool ValidateTestSmtpCertificate(
        X509Certificate2 rootCertificate,
        X509Certificate? certificate,
        SslPolicyErrors errors)
    {
        if (certificate is null || (errors & ~SslPolicyErrors.RemoteCertificateChainErrors) != SslPolicyErrors.None)
        {
            return false;
        }

        using var customChain = new X509Chain();
        customChain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        customChain.ChainPolicy.CustomTrustStore.Add(rootCertificate);
        customChain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        customChain.ChainPolicy.ApplicationPolicy.Add(new Oid("1.3.6.1.5.5.7.3.1"));
        using var leaf = X509CertificateLoader.LoadCertificate(certificate.GetRawCertData());
        return customChain.Build(leaf);
    }

    public static void UseAccountRequestPolicies(this WebApplication app)
    {
        if (!app.Services.GetRequiredService<AccountOptions>().Enabled)
        {
            return;
        }

        app.Use(async (context, next) =>
        {
            if (context.Request.Path.StartsWithSegments("/api/auth", StringComparison.OrdinalIgnoreCase)
                || context.Request.Path.StartsWithSegments("/api/books", StringComparison.OrdinalIgnoreCase)
                || context.Request.Path.StartsWithSegments("/Account", StringComparison.OrdinalIgnoreCase))
            {
                context.Response.Headers.CacheControl = "private, no-store";
                context.Response.Headers.Pragma = "no-cache";
                context.Response.OnStarting(static state =>
                {
                    var response = (HttpResponse)state;
                    response.Headers.CacheControl = "private, no-store";
                    response.Headers.Pragma = "no-cache";
                    return Task.CompletedTask;
                }, context.Response);
            }

            if (IsAccountJsonMutation(context))
            {
                var sizeFeature = context.Features.Get<IHttpMaxRequestBodySizeFeature>();
                if (sizeFeature is { IsReadOnly: false })
                {
                    sizeFeature.MaxRequestBodySize = MaximumJsonRequestBytes + 1;
                }
            }

            await next();
        });
    }

    public static void UseAccountUnsupportedIdentityRoutes(this WebApplication app)
    {
        if (!app.Services.GetRequiredService<AccountOptions>().Enabled)
        {
            return;
        }

        app.Use(async (context, next) =>
        {
            if (UnsupportedIdentityPaths.Any(path => context.Request.Path.StartsWithSegments(
                    path, StringComparison.OrdinalIgnoreCase)))
            {
                context.Response.StatusCode = StatusCodes.Status404NotFound;
                return;
            }

            await next();
        });
    }

    public static void UseAccountJsonBodyLimits(this WebApplication app)
    {
        if (!app.Services.GetRequiredService<AccountOptions>().Enabled)
        {
            return;
        }

        app.Use(async (context, next) =>
        {
            if (!IsAccountJsonMutation(context))
            {
                await next();
                return;
            }

            if (!context.Request.HasJsonContentType())
            {
                await AccountProblem.Create(StatusCodes.Status415UnsupportedMediaType, "UnsupportedMediaType",
                    "JSON required", "Send this request as application/json.")
                    .ExecuteAsync(context);
                return;
            }

            if (context.Request.ContentLength > MaximumJsonRequestBytes)
            {
                await WriteRequestTooLargeAsync(context);
                return;
            }

            var originalBody = context.Request.Body;
            var boundedBody = await BufferAtMostAsync(originalBody, MaximumJsonRequestBytes, context.RequestAborted);
            if (boundedBody is null)
            {
                await WriteRequestTooLargeAsync(context);
                return;
            }

            context.Request.Body = boundedBody;
            try
            {
                await next();
            }
            finally
            {
                context.Request.Body = originalBody;
                await boundedBody.DisposeAsync();
            }
        });
    }

    private static bool IsAccountJsonMutation(HttpContext context) =>
        AccountJsonMutationPaths.Contains(context.Request.Path.Value?.TrimEnd('/') ?? "")
        && !HttpMethods.IsGet(context.Request.Method)
        && !HttpMethods.IsHead(context.Request.Method);

    private static async Task<MemoryStream?> BufferAtMostAsync(Stream source, int limit, CancellationToken cancellationToken)
    {
        var bytes = GC.AllocateUninitializedArray<byte>(limit + 1);
        var total = 0;
        while (total < bytes.Length)
        {
            var read = await source.ReadAsync(bytes.AsMemory(total), cancellationToken);
            if (read == 0)
            {
                break;
            }
            total += read;
        }

        return total > limit ? null : new MemoryStream(bytes, 0, total, writable: false, publiclyVisible: true);
    }

    private static Task WriteRequestTooLargeAsync(HttpContext context) =>
        AccountProblem.Create(StatusCodes.Status413PayloadTooLarge, "RequestTooLarge",
            "Request too large", "The request body exceeds the 16 KiB limit.")
            .ExecuteAsync(context);
}
