using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Test.E2E.Support;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Playwright;
using Xunit;

namespace BlazorAutoApp.Test.E2E.Features.React;

[Collection(TestCollectionNames.E2E)]
public sealed class ReactPublicE2ETests(ITestOutputHelper output) : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "ReactPublicBroad")]
    public async Task AnonymousPublicFlow_IsAccessibleReadOnlyAndIsolated()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            output.WriteLine(
                "React browser={0}; version={1}; OS={2}",
                Browser.BrowserType.Name,
                Browser.Version,
                RuntimeInformation.OSDescription);

            var apiRequests = new List<IRequest>();
            var publicApiStatuses = new List<int>();
            Page.Request += (_, request) =>
            {
                if (Uri.TryCreate(request.Url, UriKind.Absolute, out var requestUri)
                    && requestUri.AbsolutePath.StartsWith("/api/", StringComparison.OrdinalIgnoreCase))
                {
                    apiRequests.Add(request);
                }
            };
            Page.Response += (_, response) =>
            {
                if (Uri.TryCreate(response.Url, UriKind.Absolute, out var responseUri)
                    && responseUri.AbsolutePath.StartsWith("/api/author-books", StringComparison.OrdinalIgnoreCase))
                {
                    publicApiStatuses.Add(response.Status);
                }
            };

            Assert.Empty(await Context.CookiesAsync());
            await GoToAsync("/");

            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Find a book that stays with you." }))
                .ToBeVisibleAsync();
            await Expect(Page).ToHaveTitleAsync("The Authors Bookcase | Independent Books");
            Assert.Equal("en", await Page.Locator("html").GetAttributeAsync("lang"));
            await AssertNoCriticalOrSeriousAxeViolationsAsync("React home page");

            var navigation = Page.GetByRole(AriaRole.Navigation, new PageGetByRoleOptions { Name = "Main navigation" });
            Assert.Equal(2, await navigation.GetByRole(AriaRole.Link).CountAsync());
            Assert.Equal(0, await Page.Locator("form").CountAsync());
            Assert.Equal(0, await Page.GetByRole(
                AriaRole.Link,
                new PageGetByRoleOptions { NameRegex = new System.Text.RegularExpressions.Regex("sign in|log in|register|account", System.Text.RegularExpressions.RegexOptions.IgnoreCase) })
                .CountAsync());

            await Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Browse the books" }).ClickAsync();
            var bookListings = Page.GetByRole(AriaRole.Region, new PageGetByRoleOptions { Name = "Public book listings" });
            await Expect(bookListings).ToBeVisibleAsync();
            var listings = bookListings.Locator("article");
            Assert.True(await listings.CountAsync() > 0, "Expected seeded public catalog books.");
            await AssertNoCriticalOrSeriousAxeViolationsAsync("React public catalog");

            var firstBook = listings.First;
            var bookTitle = (await firstBook.GetByRole(
                AriaRole.Heading,
                new LocatorGetByRoleOptions { Level = 2 }).InnerTextAsync()).Trim();
            var detailLink = firstBook.GetByRole(AriaRole.Link, new LocatorGetByRoleOptions { Name = "Explore this book" });
            var detailPath = await detailLink.GetAttributeAsync("href");
            Assert.NotNull(detailPath);
            Assert.StartsWith("/books/author/", detailPath, StringComparison.Ordinal);

            await detailLink.ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookTitle }))
                .ToBeVisibleAsync();
            await Expect(Page).ToHaveTitleAsync($"{bookTitle} | The Authors Bookcase");
            Assert.Equal(detailPath, new Uri(Page.Url).AbsolutePath);
            await AssertNoCriticalOrSeriousAxeViolationsAsync("React author-book details");

            await Page.ReloadAsync(new PageReloadOptions { WaitUntil = WaitUntilState.DOMContentLoaded });
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookTitle }))
                .ToBeVisibleAsync();
            await Page.GoBackAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Books by independent authors." }))
                .ToBeVisibleAsync();
            await Page.GoForwardAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = bookTitle }))
                .ToBeVisibleAsync();

            await SetViewportAsync(ResponsiveViewport.UltraNarrowMobile);
            await AssertNoPageHorizontalOverflowAsync("React author-book details at 320px");

            var privateBooksProbe = await Page.EvaluateAsync<string>(
                """
                async () => {
                    const response = await fetch('/api/books', { method: 'GET', credentials: 'same-origin' });
                    return JSON.stringify({
                        status: response.status,
                        contentType: response.headers.get('content-type') || '',
                        body: await response.text()
                    });
                }
                """);
            using var privateBooksDocument = JsonDocument.Parse(privateBooksProbe);
            var privateBooks = privateBooksDocument.RootElement;
            Assert.Equal(401, privateBooks.GetProperty("status").GetInt32());
            var privateBooksContentType = privateBooks.GetProperty("contentType").GetString() ?? string.Empty;
            Assert.DoesNotContain("text/html", privateBooksContentType, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("<html", privateBooks.GetProperty("body").GetString() ?? string.Empty, StringComparison.OrdinalIgnoreCase);

            var accountResponse = await GoToAsync("/Account/Login");
            Assert.NotNull(accountResponse);
            Assert.Equal(404, accountResponse.Status);
            var accountBody = await accountResponse.TextAsync();
            Assert.DoesNotContain("<html", accountBody, StringComparison.OrdinalIgnoreCase);
            Assert.Equal(0, await Page.Locator("form").CountAsync());

            Assert.NotEmpty(apiRequests);
            Assert.All(apiRequests, request => Assert.Equal("GET", request.Method));
            Assert.Contains(200, publicApiStatuses);
            Assert.Empty(await Context.CookiesAsync());
        });
    }
}
