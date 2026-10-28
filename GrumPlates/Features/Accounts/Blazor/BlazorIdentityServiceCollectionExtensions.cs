using GrumPlates.Features.Accounts.Identity;
using Microsoft.AspNetCore.Components.Authorization;

namespace GrumPlates.Features.Accounts.Blazor;

internal static class BlazorIdentityServiceCollectionExtensions
{
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
}
