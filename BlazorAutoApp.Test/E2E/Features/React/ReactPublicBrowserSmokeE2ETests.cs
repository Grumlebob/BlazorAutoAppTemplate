using System;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using BlazorAutoApp.Test.E2E.Support;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Playwright;
using Xunit;

namespace BlazorAutoApp.Test.E2E.Features.React;

[Collection(TestCollectionNames.E2E)]
public sealed class ReactPublicBrowserSmokeE2ETests(ITestOutputHelper output) : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "ReactPublicSmoke")]
    public async Task PublicCatalogAndDirectDetailLoadInSelectedBrowser()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            output.WriteLine(
                "React browser={0}; version={1}; OS={2}",
                Browser.BrowserType.Name,
                Browser.Version,
                RuntimeInformation.OSDescription);

            await GoToAsync("/books");
            var listings = Page.GetByRole(AriaRole.Region, new PageGetByRoleOptions { Name = "Public book listings" });
            await Expect(listings).ToBeVisibleAsync();

            var firstBook = listings.Locator("article").First;
            var title = (await firstBook.GetByRole(
                AriaRole.Heading,
                new LocatorGetByRoleOptions { Level = 2 }).InnerTextAsync()).Trim();
            var href = await firstBook.GetByRole(AriaRole.Link, new LocatorGetByRoleOptions { Name = "Explore this book" })
                .GetAttributeAsync("href");
            Assert.NotNull(href);

            await GoToAsync(href);
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Expect(Page).ToHaveTitleAsync($"{title} | The Authors Bookcase");
        });
    }
}
