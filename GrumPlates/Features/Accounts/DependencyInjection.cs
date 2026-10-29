using System.Net.Security;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using GrumPlates.Features.Accounts.Email;
using GrumPlates.Features.Accounts.Management;
using GrumPlates.Features.Accounts.Recovery;
using GrumPlates.Features.Accounts.Registration;
using GrumPlates.Features.Accounts.Security;
using GrumPlates.Features.Accounts.Session;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using ApplicationUser = GrumPlates.Features.Login.Account.ApplicationUser;

namespace GrumPlates.Features.Accounts;

internal static class AccountsServiceCollectionExtensions
{
    public static IServiceCollection AddAccountFeature(this IServiceCollection services, IConfiguration configuration, IHostEnvironment environment)
    {
        var settings = configuration.GetSection("Accounts").Get<AccountOptions>() ?? new();
        var validation = new AccountOptionsValidator(configuration["App:Name"] ?? "GrumPlates").Validate("Accounts", settings);
        if (validation.Failed)
        {
            throw new OptionsValidationException("Accounts", typeof(AccountOptions), validation.Failures);
        }
        services.AddSingleton(settings);
        services.AddSingleton<IOptions<AccountOptions>>(Options.Create(settings));
        var identity = new AccountApplicationIdentity(configuration["App:Name"] ?? "GrumPlates", environment.EnvironmentName);
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
        services.AddScoped<AccountMutationTransactions>();
        services.AddScoped<AccountRegistrationHandler>();
        services.AddScoped<AccountRecoveryHandler>();
        services.AddScoped<AccountRevocationHandler>();
        services.AddScoped<AccountPasswordChangeHandler>();
        services.AddScoped<AccountEmailChangeHandler>();
        services.AddScoped<AccountExportHandler>();
        services.AddScoped<AccountDeletionHandler>();
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

}
