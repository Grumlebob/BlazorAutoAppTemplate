using System;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Microsoft.Playwright.Xunit.v3;

namespace BlazorAutoApp.Test.E2E;

public abstract class BlazorE2ETestBase : PageTest
{
    private static readonly Uri BaseUri = new(GetBaseUrl());

    public override BrowserNewContextOptions ContextOptions() => new()
    {
        IgnoreHTTPSErrors = true,
        ViewportSize = new ViewportSize
        {
            Width = 1280,
            Height = 900
        }
    };

    protected Task<IResponse?> GoToAsync(string path)
    {
        var target = new Uri(BaseUri, path.TrimStart('/'));
        return Page.GotoAsync(target.ToString(), new PageGotoOptions
        {
            WaitUntil = WaitUntilState.NetworkIdle
        });
    }

    protected async Task GoHomeAndWaitForInteractivityAsync()
    {
        await GoToAsync("/");

        await Expect(Page.GetByTestId("configured-render-mode"))
            .ToContainTextAsync("Interactive Auto");
        await Expect(Page.GetByTestId("is-interactive"))
            .ToHaveTextAsync("yes", new LocatorAssertionsToHaveTextOptions { Timeout = 45_000 });
    }

    protected async Task RunWithFailureScreenshotAsync(Func<Task> test)
    {
        try
        {
            await test();
        }
        catch
        {
            var screenshotDirectory = Path.Combine("TestResults", "Playwright");
            Directory.CreateDirectory(screenshotDirectory);
            var screenshotPath = Path.Combine(
                screenshotDirectory,
                $"{GetType().Name}-{DateTimeOffset.UtcNow:yyyyMMddHHmmssfff}.png");

            await Page.ScreenshotAsync(new PageScreenshotOptions
            {
                Path = screenshotPath,
                FullPage = true
            });

            throw;
        }
    }

    private static string GetBaseUrl()
    {
        var baseUrl = Environment.GetEnvironmentVariable("E2E_BASE_URL");
        if (string.IsNullOrWhiteSpace(baseUrl))
        {
            baseUrl = "https://localhost:7186";
        }

        return baseUrl.TrimEnd('/') + "/";
    }
}
