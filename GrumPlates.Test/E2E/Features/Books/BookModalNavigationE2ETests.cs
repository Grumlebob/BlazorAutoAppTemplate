using GrumPlates.Test.E2E.Support;
using GrumPlates.Test.TestSupport.Integration;

namespace GrumPlates.Test.E2E.Features.Books;

[Collection(TestCollectionNames.E2E)]
public sealed class BookModalNavigationE2ETests : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task RapidAuthorBookNavigation_RendersAndFocusesTheLatestModal()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            await GoHomeAndWaitForInteractivityAsync();
            var books = Page.GetByTestId("author-bookcase-book");
            Assert.True(await books.CountAsync() >= 2, "Two seeded author books are required for modal navigation.");
            var firstHref = await books.Nth(0).GetAttributeAsync("href");
            var secondHref = await books.Nth(1).GetAttributeAsync("href");
            var firstLabel = await books.Nth(0).GetAttributeAsync("aria-label");
            var secondLabel = await books.Nth(1).GetAttributeAsync("aria-label");
            Assert.NotNull(firstHref);
            Assert.NotNull(secondHref);
            Assert.NotNull(firstLabel);
            Assert.NotNull(secondLabel);
            Assert.EndsWith(" details", firstLabel);
            Assert.EndsWith(" details", secondLabel);
            var firstTitle = firstLabel[..^" details".Length];
            var secondTitle = secondLabel[..^" details".Length];
            Assert.NotEqual(firstHref, secondHref);

            for (var index = 0; index < 4; index++)
            {
                var finishOnSecond = index % 2 == 0;
                var routes = finishOnSecond
                    ? new[] { secondHref, firstHref, secondHref }
                    : new[] { firstHref, secondHref, firstHref };
                await Page.EvaluateAsync("paths => { for (const path of paths) Blazor.navigateTo(path); }", routes);
                await Expect(Page.Locator("#book-modal-title"))
                    .ToHaveTextAsync(finishOnSecond ? secondTitle : firstTitle);
                await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
                await Expect(Page.GetByTestId("book-modal")).ToBeFocusedAsync();
            }

            await Page.GetByTestId("book-modal").PressAsync("Escape");
            await Expect(Page.GetByTestId("book-modal")).ToHaveCountAsync(0);
            await Expect(Page.GetByTestId("author-bookcase-title")).ToBeVisibleAsync();
        });
    }
}
