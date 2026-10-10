using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Components.Authorization;
using BlazorAutoApp.Features.Login;

namespace BlazorAutoApp.Features.Login.Account;

internal static class LoginFeatureExtensions
{
    public static IServiceCollection AddIdentityBackend(this IServiceCollection services)
    {
        services.AddHttpContextAccessor();
        services.AddAuthorization();

        var authenticationBuilder = services.AddAuthentication(options =>
        {
            options.DefaultScheme = IdentityConstants.ApplicationScheme;
            options.DefaultSignInScheme = IdentityConstants.ExternalScheme;
        });
        authenticationBuilder.AddIdentityCookies();
        services.Configure<CookieAuthenticationOptions>(
            IdentityConstants.ApplicationScheme,
            ConfigureApiCookieChallenges);

        services
            .AddIdentityCore<ApplicationUser>(options =>
            {
                options.SignIn.RequireConfirmedAccount = false;
                options.Stores.SchemaVersion = IdentitySchemaVersions.Version3;
            })
            .AddRoles<IdentityRole>()
            .AddEntityFrameworkStores<AppDbContext>()
            .AddSignInManager()
            .AddDefaultTokenProviders();

        services.AddSingleton<IEmailSender<ApplicationUser>, IdentityNoOpEmailSender>();

        return services;
    }

    public static IServiceCollection AddBlazorIdentityUi(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.AddCascadingAuthenticationState();
        services.AddScoped<IdentityRedirectManager>();
        services.AddScoped<ICurrentUserAccessor, BlazorCurrentUserAccessor>();
        services.AddScoped<AuthenticationStateProvider, IdentityRevalidatingAuthenticationStateProvider>();

        var googleClientId = configuration["Authentication:Google:ClientId"];
        var googleClientSecret = configuration["Authentication:Google:ClientSecret"];
        if (!string.IsNullOrWhiteSpace(googleClientId) && !string.IsNullOrWhiteSpace(googleClientSecret))
        {
            services.AddAuthentication().AddGoogle(options =>
            {
                options.ClientId = googleClientId;
                options.ClientSecret = googleClientSecret;
            });
        }

        return services;
    }

    // API callers (the hydrated WebAssembly client, scripts) need status codes,
    // not an HTML login page behind a 302.
    private static void ConfigureApiCookieChallenges(CookieAuthenticationOptions options)
    {
        var events = options.Events ??= new CookieAuthenticationEvents();
        events.OnRedirectToLogin = context =>
        {
            if (IsApiRequest(context.Request))
            {
                context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            }
            else
            {
                context.Response.Redirect(context.RedirectUri);
            }

            return Task.CompletedTask;
        };
        events.OnRedirectToAccessDenied = context =>
        {
            if (IsApiRequest(context.Request))
            {
                context.Response.StatusCode = StatusCodes.Status403Forbidden;
            }
            else
            {
                context.Response.Redirect(context.RedirectUri);
            }

            return Task.CompletedTask;
        };
    }

    private static bool IsApiRequest(HttpRequest request) =>
        request.Path.StartsWithSegments("/api", StringComparison.OrdinalIgnoreCase);
}
