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

            var accountLink = Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = email });
            await MakeNavigationItemVisibleAsync(accountLink);
            await Expect(accountLink)
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            var logoutButton = Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Logout" });
            await MakeNavigationItemVisibleAsync(logoutButton);
            await logoutButton.ClickAsync();
            var loginLink = Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Login" });
            await MakeNavigationItemVisibleAsync(loginLink);
            await Expect(loginLink)
                .ToBeVisibleAsync();

            await loginLink.ClickAsync();
            await Page.Locator("#Input\\.Email").FillAsync(email);
            await Page.Locator("#Input\\.Password").FillAsync(password);
            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Log in", Exact = true }).ClickAsync();
            await MakeNavigationItemVisibleAsync(accountLink);
            await Expect(accountLink)
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await accountLink.ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Profile" }))
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await GoToAsync("/Account/Manage/Passkeys");
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Manage your passkeys" }))
                .ToBeVisibleAsync();
            await Expect(Page.GetByText("No passkeys are registered.")).ToBeVisibleAsync();
            await Expect(Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Add a new passkey" }))
                .ToBeVisibleAsync();

            await MakeNavigationItemVisibleAsync(logoutButton);
            await logoutButton.ClickAsync();
            await MakeNavigationItemVisibleAsync(loginLink);
            await Expect(loginLink)
                .ToBeVisibleAsync();

            await GoToAsync("/Account/ForgotPassword");
            await Page.Locator("#Input\\.Email").FillAsync(email);
            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Reset password" }).ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Forgot password confirmation" }))
                .ToBeVisibleAsync();
        });
    }

    private async Task MakeNavigationItemVisibleAsync(ILocator locator)
    {
        if (await locator.IsVisibleAsync())
        {
            return;
        }

        await Page.GetByLabel("Toggle menu").ClickAsync();
    }
}
