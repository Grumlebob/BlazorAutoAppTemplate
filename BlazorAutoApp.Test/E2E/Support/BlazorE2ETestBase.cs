using System;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Microsoft.Playwright.Xunit.v3;

namespace BlazorAutoApp.Test.E2E.Support;

public abstract class BlazorE2ETestBase : PageTest
{
    protected const string E2EPassword = E2ETestDataCleanup.DefaultPassword;

    private static readonly Uri BaseUri = new(GetBaseUrl());
    private readonly E2ETestDataCleanup _testDataCleanup;

    protected BlazorE2ETestBase()
    {
        _testDataCleanup = new E2ETestDataCleanup(() => Page, GoToAsync);
    }

    public override Task<BrowserTypeLaunchOptions?> LaunchOptionsAsync() =>
        Task.FromResult<BrowserTypeLaunchOptions?>(new BrowserTypeLaunchOptions
        {
            Headless = IsHeadlessEnabled(),
            SlowMo = GetSlowMoMilliseconds()
        });

    public override BrowserNewContextOptions ContextOptions() => new()
    {
        IgnoreHTTPSErrors = true,
        RecordVideoDir = GetPlaywrightArtifactPath("Videos"),
        ViewportSize = new ViewportSize
        {
            Width = GetViewportDimension("E2E_VIEWPORT_WIDTH", 1280),
            Height = GetViewportDimension("E2E_VIEWPORT_HEIGHT", 900)
        }
    };

    protected Task<IResponse?> GoToAsync(string path)
    {
        var target = new Uri(BaseUri, path.TrimStart('/'));
        return Page.GotoAsync(target.ToString(), new PageGotoOptions
        {
            WaitUntil = WaitUntilState.DOMContentLoaded
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
        var artifactDirectory = GetPlaywrightArtifactPath();
        Directory.CreateDirectory(artifactDirectory);
        await Context.Tracing.StartAsync(new TracingStartOptions
        {
            Screenshots = true,
            Snapshots = true,
            Sources = true
        });

        var testFailed = false;
        try
        {
            await test();
            await Context.Tracing.StopAsync();
        }
        catch
        {
            testFailed = true;
            var tracePath = Path.Combine(
                artifactDirectory,
                $"{GetType().Name}-{DateTimeOffset.UtcNow:yyyyMMddHHmmssfff}.zip");
            await Context.Tracing.StopAsync(new TracingStopOptions { Path = tracePath });

            var screenshotPath = Path.Combine(
                artifactDirectory,
                $"{GetType().Name}-{DateTimeOffset.UtcNow:yyyyMMddHHmmssfff}.png");

            await Page.ScreenshotAsync(new PageScreenshotOptions
            {
                Path = screenshotPath,
                FullPage = true
            });

            throw;
        }
        finally
        {
            try
            {
                await _testDataCleanup.CleanupAsync();
            }
            catch (Exception ex) when (testFailed)
            {
                Console.Error.WriteLine($"E2E cleanup failed after test failure: {ex}");
            }
        }
    }

    protected void TrackCreatedUser(string email, string password = E2EPassword) =>
        _testDataCleanup.TrackCreatedUser(email, password);

    protected void TrackCreatedBook(string title, string? url = null, int? id = null) =>
        _testDataCleanup.TrackCreatedBook(title, url, id);

    protected Task TrackCreatedBookFromRowAsync(ILocator row, string title, string? url = null) =>
        _testDataCleanup.TrackCreatedBookFromRowAsync(row, title, url);

    private static string GetBaseUrl()
    {
        var baseUrl = Environment.GetEnvironmentVariable("E2E_BASE_URL");
        if (string.IsNullOrWhiteSpace(baseUrl))
        {
            baseUrl = "https://localhost:7186";
        }

        return baseUrl.TrimEnd('/') + "/";
    }

    private static bool IsHeadlessEnabled() =>
        string.Equals(Environment.GetEnvironmentVariable("E2E_HEADLESS"), "1", StringComparison.OrdinalIgnoreCase);

    private static float GetSlowMoMilliseconds()
    {
        var configured = Environment.GetEnvironmentVariable("E2E_SLOW_MO_MS");
        if (float.TryParse(configured, out var slowMo) && slowMo >= 0)
        {
            return slowMo;
        }

        return 300;
    }

    private static int GetViewportDimension(string variableName, int defaultValue)
    {
        var configured = Environment.GetEnvironmentVariable(variableName);
        if (int.TryParse(configured, out var dimension) && dimension > 0)
        {
            return dimension;
        }

        return defaultValue;
    }

    protected static string GetPlaywrightArtifactPath(params string[] segments)
    {
        var root = FindRepositoryRoot();
        var pathParts = new string[segments.Length + 3];
        pathParts[0] = root;
        pathParts[1] = "BlazorAutoApp.Test";
        pathParts[2] = Path.Combine("TestResults", "Playwright");
        Array.Copy(segments, 0, pathParts, 3, segments.Length);
        return Path.Combine(pathParts);
    }

    private static string FindRepositoryRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "BlazorAutoApp.sln")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        return AppContext.BaseDirectory;
    }
}
