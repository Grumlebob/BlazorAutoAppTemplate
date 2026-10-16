using System;
using System.Collections.Concurrent;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using BlazorAutoApp.Test.E2E.Support;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Playwright;
using MimeKit;
using Xunit;

namespace BlazorAutoApp.Test.E2E.Features.React;

[Collection(TestCollectionNames.E2E)]
public sealed class ReactPackagedAccountsE2ETests : BlazorE2ETestBase
{
    private readonly ConcurrentQueue<string> _browserErrors = new();

    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "ReactPackagedDisabled")]
    public async Task DisabledPackage_RoutesRemainPublicAndAccountViewsStayUnavailable()
    {
        MonitorBrowser(Page);
        await RunWithFailureScreenshotAsync(async () =>
        {
            var authResponse = await NavigateAsync(Page, "/auth");
            Assert.NotNull(authResponse);
            Assert.Equal(200, authResponse.Status);
            await Page.WaitForURLAsync("**/auth/login");
            Assert.Equal("/auth/login", new Uri(Page.Url).AbsolutePath);
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Accounts are unavailable" }))
                .ToBeVisibleAsync();
            await AssertCspAsync(authResponse);
            Assert.DoesNotContain(await Context.CookiesAsync(), cookie => cookie.Name.StartsWith("__Host-Accounts-", StringComparison.Ordinal));

            var booksResponse = await NavigateAsync(Page, "/my-books");
            Assert.NotNull(booksResponse);
            Assert.Equal(200, booksResponse.Status);
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "My books" })).ToBeVisibleAsync();
            await Expect(Page.GetByText("Sign in to view and save your private books.", new PageGetByTextOptions { Exact = false }))
                .ToBeVisibleAsync();
            await AssertCspAsync(booksResponse);
            Assert.Empty(await Context.CookiesAsync());
            Assert.Empty(_browserErrors);
        });
    }

    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "ReactPackagedEnabled")]
    public async Task EnabledPackage_RealMailUsersTabsAndPasswordChangeRemainPrivate()
    {
        MonitorBrowser(Page);
        await RunWithFailureScreenshotAsync(async () =>
        {
            var password = RequiredEnvironment("E2E_ACCOUNT_PASSWORD");
            var changedPassword = RequiredEnvironment("E2E_ACCOUNT_CHANGED_PASSWORD");
            var adminEmail = RequiredEnvironment("E2E_ADMIN_EMAIL");
            var adminPassword = RequiredEnvironment("E2E_ADMIN_PASSWORD");

            await AssertSeededAdminAsync(adminEmail, adminPassword);

            var authResponse = await NavigateAsync(Page, "/auth");
            Assert.NotNull(authResponse);
            Assert.Equal(200, authResponse.Status);
            await Page.WaitForURLAsync("**/auth/login");
            Assert.Equal("/auth/login", new Uri(Page.Url).AbsolutePath);
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Sign in" })).ToBeVisibleAsync();
            await AssertCspAsync(authResponse);
            Assert.DoesNotContain(await Context.CookiesAsync(), cookie => cookie.Name.StartsWith("__Host-Accounts-", StringComparison.Ordinal));

            var anonBooksResponse = await NavigateAsync(Page, "/my-books");
            Assert.NotNull(anonBooksResponse);
            Assert.Equal(200, anonBooksResponse.Status);
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "My books" })).ToBeVisibleAsync();
            await Expect(Page.GetByText("Sign in to view and save your private books.", new PageGetByTextOptions { Exact = false }))
                .ToBeVisibleAsync();
            await AssertCspAsync(anonBooksResponse);
            Assert.DoesNotContain(await Context.CookiesAsync(), cookie => cookie.Name.StartsWith("__Host-Accounts-", StringComparison.Ordinal));

            var userA = NewEmail("react-a");
            var userAPassword = password;
            TrackCreatedUser(userA, userAPassword);
            await RegisterAndConfirmAsync(Page, userA, userAPassword);
            await SignInAsync(Page, userA, userAPassword);
            AssertAuthenticationCookies(await Context.CookiesAsync());

            var bookA = $"E2E Book React {Guid.NewGuid():N}";
            TrackCreatedBook(bookA);
            await AddBookAsync(Page, bookA, "React User A");
            await ReloadAndAssertBookAsync(Page, bookA);

            var userASecondSession = await Browser.NewContextAsync(ContextOptions());
            try
            {
                var userASecondTab = await userASecondSession.NewPageAsync();
                MonitorBrowser(userASecondTab);
                await SignInAsync(userASecondTab, userA, userAPassword);
                await Expect(userASecondTab.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookA })).ToBeVisibleAsync();
                var secondSessionCookies = await userASecondSession.CookiesAsync();
                AssertAuthenticationCookies(secondSessionCookies);

                var userB = NewEmail("react-b");
                TrackCreatedUser(userB, password);
                var userBContext = await Browser.NewContextAsync(ContextOptions());
                try
                {
                    var userBPage = await userBContext.NewPageAsync();
                    MonitorBrowser(userBPage);
                    await RegisterAndConfirmAsync(userBPage, userB, password);
                    await SignInAsync(userBPage, userB, password);
                    await Expect(userBPage.GetByText("No books yet. Add your first below.", new PageGetByTextOptions { Exact = false }))
                        .ToBeVisibleAsync();
                    Assert.False(await userBPage.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookA }).IsVisibleAsync());

                    var bookB = $"E2E Book React {Guid.NewGuid():N}";
                    TrackCreatedBook(bookB);
                    await AddBookAsync(userBPage, bookB, "React User B");
                    await ReloadAndAssertBookAsync(userBPage, bookB);
                    Assert.False(await userBPage.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookA }).IsVisibleAsync());

                    await NavigateAsync(Page, "/auth/settings");
                    await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Your account" })).ToBeVisibleAsync();
                    await Page.Locator("input[autocomplete='current-password']").FillAsync(userAPassword);
                    await Page.Locator("input[name='newPassword']").FillAsync(changedPassword);
                    await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Change password" }).ClickAsync();
                    await Expect(Page.GetByText("Sign in to manage your account.", new PageGetByTextOptions { Exact = false }))
                        .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

                    await NavigateAsync(userASecondTab, "/my-books");
                    await Expect(userASecondTab.GetByText("Sign in to view and save your private books.", new PageGetByTextOptions { Exact = false }))
                        .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
                    Assert.False(await userASecondTab.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookA }).IsVisibleAsync());

                    await ReloadAndAssertBookAsync(userBPage, bookB);
                    await SignInAsync(Page, userA, changedPassword);
                    await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookA })).ToBeVisibleAsync();
                    Assert.False(await Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookB }).IsVisibleAsync());
                    Assert.Empty(_browserErrors);
                }
                finally
                {
                    await userBContext.CloseAsync();
                }
            }
            finally
            {
                await userASecondSession.CloseAsync();
            }
        });
    }

    private async Task AssertSeededAdminAsync(string email, string password)
    {
        var context = await Browser.NewContextAsync(ContextOptions());
        try
        {
            var page = await context.NewPageAsync();
            MonitorBrowser(page);
            await SignInAsync(page, email, password);
            await NavigateAsync(page, "/auth/settings");
            await Expect(page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Your account" })).ToBeVisibleAsync();
            await Expect(page.GetByText("Admin", new PageGetByTextOptions { Exact = true })).ToBeVisibleAsync();
            AssertAuthenticationCookies(await context.CookiesAsync());
        }
        finally
        {
            await context.CloseAsync();
        }
    }

    private async Task RegisterAndConfirmAsync(IPage page, string email, string password)
    {
        var response = await NavigateAsync(page, "/auth/register");
        Assert.NotNull(response);
        Assert.Equal(200, response.Status);
        await Expect(page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Create an account" })).ToBeVisibleAsync();
        await page.GetByLabel("Email").FillAsync(email);
        await page.GetByLabel("Email").PressAsync("Enter");
        await Expect(page.GetByRole(AriaRole.Status)).ToContainTextAsync("Request received", new LocatorAssertionsToContainTextOptions { Timeout = 30_000 });

        var confirmationLink = await WaitForMailLinkAsync(email, "/auth/confirm-email");
        var uri = new Uri(confirmationLink);
        Assert.Equal(new Uri(BaseUrl()).Authority, uri.Authority);
        Assert.Equal("/auth/confirm-email", uri.AbsolutePath);
        Assert.Empty(uri.Query);
        Assert.Contains("userId=", uri.Fragment, StringComparison.Ordinal);
        Assert.Contains("token=", uri.Fragment, StringComparison.Ordinal);
        Assert.DoesNotContain("token=", uri.PathAndQuery, StringComparison.Ordinal);

        var confirmResponse = await page.GotoAsync(confirmationLink, new PageGotoOptions { WaitUntil = WaitUntilState.DOMContentLoaded });
        Assert.NotNull(confirmResponse);
        Assert.Equal(200, confirmResponse.Status);
        await Expect(page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Confirm your email" })).ToBeVisibleAsync();
        var passwordField = page.Locator("input[name='newPassword']");
        await passwordField.FillAsync(password);
        await passwordField.PressAsync("Enter");
        await Expect(page.GetByRole(AriaRole.Status)).ToContainTextAsync("Email confirmed", new LocatorAssertionsToContainTextOptions { Timeout = 30_000 });
        Assert.Empty(new Uri(page.Url).Fragment);
    }

    private async Task SignInAsync(IPage page, string email, string password)
    {
        await NavigateAsync(page, "/auth/login?returnTo=%2Fmy-books");
        await Expect(page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Sign in" })).ToBeVisibleAsync();
        await page.GetByLabel("Email").FillAsync(email);
        var passwordField = page.Locator("input[name='password']");
        await passwordField.FillAsync(password);
        await passwordField.PressAsync("Enter");
        await Expect(page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "My books" }))
            .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
    }

    private async Task AddBookAsync(IPage page, string title, string author)
    {
        await page.GetByLabel("Title").FillAsync(title);
        await page.GetByLabel("Author").FillAsync(author);
        await page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Save book" }).ClickAsync();
        await Expect(page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title })).ToBeVisibleAsync();
    }

    private async Task ReloadAndAssertBookAsync(IPage page, string title)
    {
        await page.ReloadAsync(new PageReloadOptions { WaitUntil = WaitUntilState.DOMContentLoaded });
        await Expect(page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title }))
            .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
    }

    private static async Task<string> WaitForMailLinkAsync(string recipient, string requiredPath)
    {
        var directory = RequiredEnvironment("E2E_SMTP_CAPTURE_DIR");
        var deadline = DateTimeOffset.UtcNow.AddSeconds(90);
        while (DateTimeOffset.UtcNow < deadline)
        {
            foreach (var path in Directory.EnumerateFiles(directory, "*.eml"))
            {
                try
                {
                    using var stream = File.OpenRead(path);
                    var message = MimeMessage.Load(stream);
                    if (!message.To.Mailboxes.Any(mailbox => string.Equals(mailbox.Address, recipient, StringComparison.OrdinalIgnoreCase)))
                    {
                        continue;
                    }

                    var text = message.TextBody ?? string.Empty;
                    var match = Regex.Match(text, @"https://[^\s<>]+", RegexOptions.CultureInvariant);
                    if (match.Success && Uri.TryCreate(match.Value.TrimEnd('.', ',', ')'), UriKind.Absolute, out var uri)
                        && string.Equals(uri.AbsolutePath, requiredPath, StringComparison.Ordinal))
                    {
                        return uri.ToString();
                    }
                }
                catch (IOException)
                {
                    // The SMTP fixture writes with create-new and the next poll will see the completed file.
                }
            }

            await Task.Delay(250);
        }

        throw new TimeoutException("The SMTP fixture did not capture the expected account message.");
    }

    private static async Task AssertCspAsync(IResponse response)
    {
        var headers = await response.AllHeadersAsync();
        Assert.True(headers.TryGetValue("content-security-policy", out var csp), "Packaged React response has no CSP header.");
        Assert.NotNull(csp);
        Assert.Contains("default-src 'self'", csp, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("sha256-", csp, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("unsafe-inline", csp, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("unsafe-eval", csp, StringComparison.OrdinalIgnoreCase);
    }

    private static void AssertAuthenticationCookies(System.Collections.Generic.IReadOnlyList<BrowserContextCookiesResult> cookies)
    {
        var authCookie = Assert.Single(cookies, cookie => cookie.Name.StartsWith("__Host-Accounts-", StringComparison.Ordinal));
        Assert.True(authCookie.HttpOnly);
        Assert.True(authCookie.Secure);
        Assert.Equal(SameSiteAttribute.Lax, authCookie.SameSite);

        var csrfCookie = Assert.Single(cookies, cookie => cookie.Name.StartsWith("__Host-CSRF-", StringComparison.Ordinal));
        Assert.True(csrfCookie.Secure);
        Assert.Equal(SameSiteAttribute.Strict, csrfCookie.SameSite);
    }

    private void MonitorBrowser(IPage page)
    {
        page.Console += (_, message) =>
        {
            if (message.Type == "error")
            {
                _browserErrors.Enqueue(message.Text);
            }
        };
        page.PageError += (_, error) => _browserErrors.Enqueue(error);
    }

    private static Task<IResponse?> NavigateAsync(IPage page, string path)
    {
        var target = new Uri(new Uri(BaseUrl()), path.TrimStart('/'));
        return page.GotoAsync(target.ToString(), new PageGotoOptions { WaitUntil = WaitUntilState.DOMContentLoaded });
    }

    private static string BaseUrl()
    {
        var value = RequiredEnvironment("E2E_BASE_URL").TrimEnd('/');
        return value + "/";
    }

    private static string RequiredEnvironment(string name)
    {
        var value = Environment.GetEnvironmentVariable(name);
        return !string.IsNullOrWhiteSpace(value)
            ? value
            : throw new InvalidOperationException($"{name} must be set for the packaged React account browser suite.");
    }

    private static string NewEmail(string prefix) => $"{prefix}-{Guid.NewGuid():N}@example.test";
}
