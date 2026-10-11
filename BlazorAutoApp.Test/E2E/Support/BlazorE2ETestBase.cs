using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Microsoft.Playwright.Xunit.v3;
using Xunit;

namespace BlazorAutoApp.Test.E2E.Support;

public abstract class BlazorE2ETestBase : PageTest
{
    protected const string E2EPassword = E2ETestCredentials.Password;

    private static readonly JsonSerializerOptions AxeJsonOptions = new(JsonSerializerDefaults.Web);
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

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = new BrowserNewContextOptions
        {
            IgnoreHTTPSErrors = true,
            ViewportSize = new ViewportSize
            {
                Width = GetViewportDimension("E2E_VIEWPORT_WIDTH", 1280),
                Height = GetViewportDimension("E2E_VIEWPORT_HEIGHT", 900)
            }
        };

        if (IsVideoRecordingEnabled())
        {
            options.RecordVideoDir = GetPlaywrightArtifactPath("Videos");
        }

        return options;
    }

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

        await WaitForInteractivityAsync();
    }

    protected async Task ReloadAndWaitForInteractivityAsync()
    {
        await Page.ReloadAsync(new PageReloadOptions
        {
            WaitUntil = WaitUntilState.DOMContentLoaded
        });

        await WaitForInteractivityAsync();
    }

    protected async Task WaitForInteractivityAsync()
    {
        await Expect(Page.GetByTestId("app-interactivity-probe"))
            .ToHaveAttributeAsync(
                "data-interactive",
                "true",
                new LocatorAssertionsToHaveAttributeOptions { Timeout = 45_000 });
    }

    protected async Task<bool> BrowserApiRequestsAreObservableAsync()
    {
        var renderer = await Page
            .GetByTestId("app-interactivity-probe")
            .GetAttributeAsync("data-current-renderer");

        Assert.True(
            renderer is "Server" or "WebAssembly",
            $"Expected hydrated renderer to be Server or WebAssembly, but was '{renderer}'.");

        return string.Equals(renderer, "WebAssembly", StringComparison.Ordinal);
    }

    protected async Task SkipIfBrowserApiRequestsAreNotObservableAsync(string context)
    {
        if (!await BrowserApiRequestsAreObservableAsync())
        {
            Assert.Skip(
                $"{context} requires browser-observable API requests; Interactive Server keeps the call inside the Blazor circuit.");
        }
    }

    protected Task SetViewportAsync(ResponsiveViewport viewport) =>
        Page.SetViewportSizeAsync(viewport.Width, viewport.Height);

    protected async Task AssertNoPageHorizontalOverflowAsync(string context)
    {
        var overflowReport = await Page.EvaluateAsync<string?>(
            """
            () => {
                const documentElement = document.documentElement;
                const body = document.body;
                const viewportWidth = documentElement.clientWidth || window.innerWidth;
                const scrollWidth = Math.max(documentElement.scrollWidth, body ? body.scrollWidth : 0);
                if (scrollWidth <= viewportWidth + 1) {
                    return null;
                }

                const offenders = Array.from(document.body.querySelectorAll('*'))
                    .filter(element => {
                        const style = window.getComputedStyle(element);
                        if (style.display === 'none' || style.visibility === 'hidden') {
                            return false;
                        }

                        const rect = element.getBoundingClientRect();
                        return rect.width > 0 &&
                            rect.height > 0 &&
                            rect.right > viewportWidth + 1 &&
                            style.position !== 'fixed';
                    })
                    .slice(0, 8)
                    .map(element => {
                        const id = element.id ? `#${element.id}` : '';
                        const testId = element.getAttribute('data-testid');
                        const testIdText = testId ? `[data-testid="${testId}"]` : '';
                        const classes = typeof element.className === 'string' && element.className
                            ? `.${element.className.trim().split(/\s+/).slice(0, 3).join('.')}`
                            : '';
                        const rect = element.getBoundingClientRect();
                        return `${element.tagName.toLowerCase()}${id}${testIdText}${classes} right=${Math.round(rect.right)}`;
                    });

                return `viewport=${viewportWidth}, scrollWidth=${scrollWidth}, offenders=${offenders.join('; ')}`;
            }
            """);

        Assert.True(overflowReport is null, $"{context} has horizontal overflow: {overflowReport}");
    }

    protected async Task AssertNoVisibleBrokenImagesAsync(string context)
    {
        var deadline = DateTimeOffset.UtcNow.AddSeconds(15);
        string? brokenImages;
        do
        {
            brokenImages = await GetVisibleBrokenImagesReportAsync();
            if (brokenImages is null)
            {
                return;
            }

            await Task.Delay(250);
        }
        while (DateTimeOffset.UtcNow < deadline);

        Assert.True(brokenImages is null, $"{context} has visible broken images: {brokenImages}");
    }

    private async Task<string?> GetVisibleBrokenImagesReportAsync()
    {
        return await Page.EvaluateAsync<string?>(
            """
            () => {
                const broken = Array.from(document.images)
                    .filter(image => {
                        const style = window.getComputedStyle(image);
                        const rect = image.getBoundingClientRect();
                        return style.display !== 'none' &&
                            style.visibility !== 'hidden' &&
                            rect.width > 1 &&
                            rect.height > 1 &&
                            image.complete &&
                            image.naturalWidth === 0;
                    })
                    .slice(0, 8)
                    .map(image => {
                        const testId = image.getAttribute('data-testid');
                        const testIdText = testId ? `[data-testid="${testId}"]` : '';
                        const alt = image.getAttribute('alt') || '';
                        return `${testIdText}${image.currentSrc || image.src} alt="${alt}"`;
                    });

                return broken.length === 0 ? null : broken.join('; ');
            }
            """);
    }

    protected static async Task AssertImageLoadedAsync(ILocator locator, string context)
    {
        await locator.WaitForAsync(new LocatorWaitForOptions { State = WaitForSelectorState.Visible });
        var deadline = DateTimeOffset.UtcNow.AddSeconds(15);
        string? loadReport;
        do
        {
            loadReport = await locator.EvaluateAsync<string?>(
                """
                image => {
                    if (image.complete && image.naturalWidth > 0 && image.naturalHeight > 0) {
                        return null;
                    }

                    const testId = image.getAttribute('data-testid');
                    const testIdText = testId ? `[data-testid="${testId}"]` : '';
                    return `${testIdText}${image.currentSrc || image.src} complete=${image.complete} natural=${image.naturalWidth}x${image.naturalHeight}`;
                }
                """);
            if (loadReport is null)
            {
                return;
            }

            await Task.Delay(250);
        }
        while (DateTimeOffset.UtcNow < deadline);

        Assert.True(loadReport is null, $"{context} image did not load: {loadReport}");
    }

    protected async Task AssertNoInsecureImageSourcesAsync(string context)
    {
        var insecureImages = await Page.EvaluateAsync<string?>(
            """
            () => {
                if (window.location.protocol !== 'https:') {
                    return null;
                }

                const insecure = Array.from(document.images)
                    .filter(image => {
                        const source = image.currentSrc || image.src || '';
                        return source.startsWith('http://');
                    })
                    .slice(0, 8)
                    .map(image => {
                        const testId = image.getAttribute('data-testid');
                        const testIdText = testId ? `[data-testid="${testId}"]` : '';
                        const alt = image.getAttribute('alt') || '';
                        return `${testIdText}${image.currentSrc || image.src} alt="${alt}"`;
                    });

                return insecure.length === 0 ? null : insecure.join('; ');
            }
            """);

        Assert.True(insecureImages is null, $"{context} has insecure image sources: {insecureImages}");
    }

    protected async Task AssertNoCriticalOrSeriousAxeViolationsAsync(string context, string? includeSelector = null)
    {
        var axeLoaded = await Page.EvaluateAsync<bool>("() => Boolean(window.axe)");
        if (!axeLoaded)
        {
            var axeUrl = Environment.GetEnvironmentVariable("E2E_AXE_URL");
            if (!string.IsNullOrWhiteSpace(axeUrl))
            {
                var pageOrigin = new Uri(Page.Url).GetLeftPart(UriPartial.Authority);
                Assert.Equal(pageOrigin, new Uri(axeUrl).GetLeftPart(UriPartial.Authority));
                await Page.AddScriptTagAsync(new PageAddScriptTagOptions { Url = axeUrl });
            }
            else
            {
                var axePath = GetRepositoryPath("BlazorAutoApp.Client", "node_modules", "axe-core", "axe.min.js");
                Assert.True(
                    File.Exists(axePath),
                    $"axe-core script was not found at {axePath}. Run `npm --prefix BlazorAutoApp.Client ci` before axe-enabled E2E tests.");
                await Page.AddScriptTagAsync(new PageAddScriptTagOptions { Path = axePath });
            }
        }

        var reportJson = await Page.EvaluateAsync<string>(
            """
            async selector => {
                const root = selector ? document.querySelector(selector) : document;
                if (!root) {
                    return JSON.stringify({
                        missingSelector: selector,
                        violations: []
                    });
                }

                const results = await window.axe.run(root, {
                    runOnly: {
                        type: 'tag',
                        values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
                    }
                });
                const severeImpacts = new Set(['critical', 'serious']);

                return JSON.stringify({
                    missingSelector: null,
                    violations: results.violations
                        .filter(violation => severeImpacts.has(violation.impact))
                        .map(violation => ({
                            id: violation.id,
                            impact: violation.impact,
                            help: violation.help,
                            helpUrl: violation.helpUrl,
                            nodes: violation.nodes.slice(0, 5).map(node => ({
                                target: node.target.join(' '),
                                summary: node.failureSummary || ''
                            }))
                        }))
                });
            }
            """,
            includeSelector);
        var report = JsonSerializer.Deserialize<AxeReport>(reportJson, AxeJsonOptions)
            ?? throw new InvalidOperationException("Axe did not return a valid report.");

        Assert.True(
            report.MissingSelector is null,
            $"Axe scope selector was not found for {context}: {report.MissingSelector}");

        if (report.Violations.Length == 0)
        {
            return;
        }

        var violations = report.Violations
            .Select(violation =>
            {
                var nodes = string.Join(
                    " | ",
                    violation.Nodes.Select(node => $"{node.Target}: {node.Summary.ReplaceLineEndings(" ")}"));
                return $"{violation.Impact} {violation.Id}: {violation.Help} ({violation.HelpUrl}) targets={nodes}";
            });

        Assert.Fail($"{context} has critical/serious accessibility violations: {string.Join("; ", violations)}");
    }

    protected static async Task AssertCssColorAsync(ILocator locator, string expectedColor, string context)
    {
        var color = await locator.EvaluateAsync<string>("element => getComputedStyle(element).color");
        Assert.Equal(expectedColor, color);
    }

    protected static async Task AssertCssColorInAsync(ILocator locator, IReadOnlyCollection<string> expectedColors, string context)
    {
        var color = await locator.EvaluateAsync<string>("element => getComputedStyle(element).color");
        Assert.Contains(color, expectedColors);
    }

    protected async Task CaptureVisualAuditScreenshotAsync(
        string area,
        string name,
        ResponsiveViewport viewport,
        string reviewFolder = "responsive-audit")
    {
        var screenshotPath = GetVisualBaselineArtifactPath(
            "current-review",
            reviewFolder,
            area,
            $"{viewport.Label}-{name}.png");
        await CaptureFullPageScreenshotAsync(screenshotPath);
    }

    protected async Task RunWithFailureScreenshotAsync(Func<Task> test)
    {
        var artifactDirectory = GetPlaywrightArtifactPath();
        Directory.CreateDirectory(artifactDirectory);
        Page.SetDefaultNavigationTimeout(GetTimeoutMilliseconds("E2E_NAVIGATION_TIMEOUT_MS", 90_000));
        Page.SetDefaultTimeout(GetTimeoutMilliseconds("E2E_ACTION_TIMEOUT_MS", 45_000));
        var browserDiagnostics = new List<string>();
        Page.Console += (_, message) => browserDiagnostics.Add(
            $"console {message.Type}: {message.Text}");
        Page.PageError += (_, error) => browserDiagnostics.Add($"pageerror: {error}");
        Page.RequestFailed += (_, request) => browserDiagnostics.Add(
            $"requestfailed {request.Method} {request.Url}: {request.Failure}");
        Page.Response += (_, response) =>
        {
            if (response.Status >= 400)
            {
                browserDiagnostics.Add($"response {response.Status} {response.Url}");
            }
        };

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
            await TryStopTracingAfterFailureAsync(tracePath);

            var screenshotPath = Path.Combine(
                artifactDirectory,
                $"{GetType().Name}-{DateTimeOffset.UtcNow:yyyyMMddHHmmssfff}.png");

            try
            {
                await Page.ScreenshotAsync(new PageScreenshotOptions
                {
                    Path = screenshotPath,
                    FullPage = true,
                    Timeout = 10_000
                });
            }
            catch (Exception screenshotException)
            {
                Console.Error.WriteLine($"E2E failure screenshot failed: {screenshotException}");
            }

            WriteBrowserDiagnostics(artifactDirectory, browserDiagnostics);

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

    protected async Task<string> RegisterUniqueUserAsync(string emailPrefix)
    {
        var suffix = Guid.NewGuid().ToString("N")[..10];
        var email = $"{emailPrefix}-{suffix}@example.test";
        TrackCreatedUser(email);

        await GoToAsync("/Account/Register");
        await Page.Locator("#Input\\.Email").FillAsync(email);
        await Page.Locator("#Input\\.Password").FillAsync(E2EPassword);
        await Page.Locator("#Input\\.ConfirmPassword").FillAsync(E2EPassword);
        await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Register" }).ClickAsync();
        await Expect(Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = email }).First)
            .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

        return email;
    }

    private async Task TryStopTracingAfterFailureAsync(string tracePath)
    {
        try
        {
            await Context.Tracing.StopAsync(new TracingStopOptions { Path = tracePath });
        }
        catch (Exception traceException)
        {
            Console.Error.WriteLine($"E2E failure trace capture failed: {traceException}");
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

    private static bool IsHeadlessEnabled() =>
        string.Equals(Environment.GetEnvironmentVariable("E2E_HEADLESS"), "1", StringComparison.OrdinalIgnoreCase);

    private static bool IsVideoRecordingEnabled() =>
        string.Equals(Environment.GetEnvironmentVariable("E2E_RECORD_VIDEO"), "1", StringComparison.OrdinalIgnoreCase);

    private static float GetSlowMoMilliseconds()
    {
        var configured = Environment.GetEnvironmentVariable("E2E_SLOW_MO_MS");
        if (float.TryParse(configured, out var slowMo) && slowMo >= 0)
        {
            return slowMo;
        }

        return 300;
    }

    private static float GetTimeoutMilliseconds(string variableName, float defaultValue)
    {
        var configured = Environment.GetEnvironmentVariable(variableName);
        if (float.TryParse(configured, out var timeout) && timeout > 0)
        {
            return timeout;
        }

        return defaultValue;
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
        => E2EArtifactPaths.PlaywrightPath(segments);

    protected static string GetRepositoryPath(params string[] segments) =>
        E2EArtifactPaths.RepositoryPath(segments);

    protected static string GetVisualBaselineArtifactPath(params string[] segments) =>
        E2EArtifactPaths.VisualBaselinePath(segments);

    protected async Task CaptureFullPageScreenshotAsync(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path) ?? throw new InvalidOperationException("Missing screenshot directory."));
        await Page.ScreenshotAsync(new PageScreenshotOptions
        {
            Path = path,
            FullPage = true
        });
    }

    private static void WriteBrowserDiagnostics(string artifactDirectory, IReadOnlyCollection<string> diagnostics)
    {
        if (diagnostics.Count == 0)
        {
            return;
        }

        var diagnosticsPath = Path.Combine(
            artifactDirectory,
            $"browser-diagnostics-{DateTimeOffset.UtcNow:yyyyMMddHHmmssfff}.log");
        var lines = diagnostics
            .Select(line => line.Replace(Environment.NewLine, " ", StringComparison.Ordinal))
            .ToArray();
        File.WriteAllLines(diagnosticsPath, lines);
        Console.Error.WriteLine($"Browser diagnostics written to {diagnosticsPath}");
        foreach (var line in lines.TakeLast(20))
        {
            Console.Error.WriteLine(line);
        }
    }

    private sealed record AxeReport(string? MissingSelector, AxeViolation[] Violations);

    private sealed record AxeViolation(string Id, string Impact, string Help, string HelpUrl, AxeNode[] Nodes);

    private sealed record AxeNode(string Target, string Summary);
}
