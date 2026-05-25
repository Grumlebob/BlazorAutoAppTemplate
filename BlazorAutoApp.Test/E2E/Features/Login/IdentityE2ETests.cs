using System;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Xunit;
using BlazorAutoApp.Test.E2E.Support;

namespace BlazorAutoApp.Test.E2E.Features.Login;

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
            var visibleAccountLink = await MakeNavigationItemVisibleAsync(accountLink);
            await Expect(visibleAccountLink)
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            var logoutButton = Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Logout" });
            var visibleLogoutButton = await MakeNavigationItemVisibleAsync(logoutButton);
            await visibleLogoutButton.ClickAsync();
            var loginLink = Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Login" });
            var visibleLoginLink = await MakeNavigationItemVisibleAsync(loginLink);
            await Expect(visibleLoginLink)
                .ToBeVisibleAsync();

            await visibleLoginLink.ClickAsync();
            await Page.Locator("#Input\\.Email").FillAsync(email);
            await Page.Locator("#Input\\.Password").FillAsync(password);
            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Log in", Exact = true }).ClickAsync();
            visibleAccountLink = await MakeNavigationItemVisibleAsync(accountLink);
            await Expect(visibleAccountLink)
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await visibleAccountLink.ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Profile" }))
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await GoToAsync("/Account/Manage/Passkeys");
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Manage your passkeys" }))
                .ToBeVisibleAsync();
            await Expect(Page.GetByText("No passkeys are registered.")).ToBeVisibleAsync();
            await Expect(Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Add a new passkey" }))
                .ToBeVisibleAsync();

            visibleLogoutButton = await MakeNavigationItemVisibleAsync(logoutButton);
            await visibleLogoutButton.ClickAsync();
            visibleLoginLink = await MakeNavigationItemVisibleAsync(loginLink);
            await Expect(visibleLoginLink)
                .ToBeVisibleAsync();

            await GoToAsync("/Account/ForgotPassword");
            await Page.Locator("#Input\\.Email").FillAsync(email);
            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Reset password" }).ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Forgot password confirmation" }))
                .ToBeVisibleAsync();
        });
    }

    private async Task<ILocator> MakeNavigationItemVisibleAsync(ILocator locator)
    {
        var deadline = DateTimeOffset.UtcNow.AddSeconds(30);
        while (DateTimeOffset.UtcNow < deadline)
        {
            var visible = await FirstVisibleAsync(locator);
            if (visible is not null)
            {
                return visible;
            }

            await OpenMobileNavigationMenuAsync();
            await Task.Delay(250);
        }

        await Expect(locator.First).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 5_000 });
        return locator.First;
    }

    private static async Task<ILocator?> FirstVisibleAsync(ILocator locator)
    {
        var count = await locator.CountAsync();
        for (var i = 0; i < count; i++)
        {
            var candidate = locator.Nth(i);
            if (await candidate.IsVisibleAsync())
            {
                return candidate;
            }
        }

        return null;
    }

    private async Task OpenMobileNavigationMenuAsync()
    {
        var mobileMenu = Page.GetByTestId("nav-menu");
        if (await mobileMenu.CountAsync() > 0)
        {
            await mobileMenu.EvaluateAsync("element => element.setAttribute('open', '')");
        }
    }
}
