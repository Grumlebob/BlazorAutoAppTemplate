using BlazorAutoApp.Features.Login;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Frontend;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Architecture.Composition;

public sealed class FrontendCompositionTests
{
    [Fact]
    public async Task SelectedComposition_RegistersOnlyItsFrontendServices()
    {
        var services = new ServiceCollection();
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Authentication:Google:ClientId"] = "test-client",
                ["Authentication:Google:ClientSecret"] = "test-secret"
            })
            .Build();

        services.AddIdentityBackend();
        FrontendComposition.AddFrontendServices(services, configuration);

        var currentUser = Assert.Single(services, descriptor => descriptor.ServiceType == typeof(ICurrentUserAccessor));
        Assert.NotNull(currentUser.ImplementationType);
        using var provider = services.BuildServiceProvider();
        var schemes = await provider.GetRequiredService<IAuthenticationSchemeProvider>().GetAllSchemesAsync();

        Assert.Contains(schemes, scheme => scheme.Name == IdentityConstants.ApplicationScheme);

        if (currentUser.ImplementationType == typeof(BlazorCurrentUserAccessor))
        {
            Assert.Contains(services, descriptor =>
                descriptor.ServiceType == typeof(AuthenticationStateProvider)
                && descriptor.ImplementationType == typeof(IdentityRevalidatingAuthenticationStateProvider));
            Assert.Contains(services, descriptor => descriptor.ServiceType == typeof(IdentityRedirectManager));
            Assert.Contains(services, descriptor => descriptor.ServiceType.Name == "AuthorBookcaseState");
            Assert.Contains(services, descriptor => descriptor.ServiceType.Name == "UserBookcaseState");
            Assert.Contains(schemes, scheme => scheme.Name == "Google");
        }
        else
        {
            Assert.Equal(typeof(HttpPrincipalCurrentUserAccessor), currentUser.ImplementationType);
            Assert.DoesNotContain(services, descriptor => descriptor.ServiceType == typeof(AuthenticationStateProvider));
            Assert.DoesNotContain(services, descriptor => descriptor.ServiceType == typeof(IdentityRedirectManager));
            Assert.DoesNotContain(services, descriptor =>
                descriptor.ServiceType.Namespace?.StartsWith("Microsoft.AspNetCore.Components", StringComparison.Ordinal) == true);
            Assert.DoesNotContain(schemes, scheme => scheme.Name == "Google");
        }
    }
}
