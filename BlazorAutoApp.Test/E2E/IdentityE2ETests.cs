using System;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Xunit;

namespace BlazorAutoApp.Test.E2E;

public sealed class IdentityE2ETests : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task Identity_CanRegisterLogoutLoginAndOpenProfile()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            var suffix = Guid.NewGuid().ToString("N")[..10];
            var email = $"e2e-{suffix}@example.test";
            const string password = "Passw0rd!";

            await GoToAsync("/Account/Register");
            await Page.Locator("#Input\\.Email").FillAsync(email);
            await Page.Locator("#Input\\.Password").FillAsync(password);
            await Page.Locator("#Input\\.ConfirmPassword").FillAsync(password);
            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Register" }).ClickAsync();
            await Page.WaitForLoadStateAsync(LoadState.NetworkIdle);

            await Expect(Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = email }))
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Logout" }).ClickAsync();
            await Page.WaitForLoadStateAsync(LoadState.NetworkIdle);
            await Expect(Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Login" }))
                .ToBeVisibleAsync();

            await Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Login" }).ClickAsync();
            await Page.Locator("#Input\\.Email").FillAsync(email);
            await Page.Locator("#Input\\.Password").FillAsync(password);
            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Log in", Exact = true }).ClickAsync();
            await Page.WaitForLoadStateAsync(LoadState.NetworkIdle);

            await Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = email }).ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Profile" }))
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
        });
    }
}
