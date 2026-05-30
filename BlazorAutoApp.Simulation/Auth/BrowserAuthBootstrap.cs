using System.Diagnostics;
using System.Net;
using Microsoft.Playwright;
using BlazorAutoApp.Simulation.Http;

namespace BlazorAutoApp.Simulation.Auth;

internal sealed class BrowserAuthBootstrap
{
    private const int DefaultTimeoutMs = 30_000;

    private readonly AuthBootstrapOptions _options;

    public BrowserAuthBootstrap(AuthBootstrapOptions options)
    {
        _options = options;
    }

    public async Task<AuthenticatedSession> BootstrapAsync(CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();
        var playwright = await Playwright.CreateAsync();
        IBrowser? browser = null;
        IBrowserContext? context = null;

        try
        {
            browser = await playwright.Chromium.LaunchAsync(new BrowserTypeLaunchOptions
            {
                Headless = !_options.HeadedBrowser
            });

            context = await browser.NewContextAsync(new BrowserNewContextOptions
            {
                IgnoreHTTPSErrors = HttpClientFactory.IsLocalhost(_options.BaseUrl)
            });

            var page = await context.NewPageAsync();
            var loggedIn = await TryLoginAsync(page, cancellationToken);
            var registered = false;
            if (!loggedIn && _options.RegisterSyntheticUser)
            {
                registered = await TryRegisterAsync(page, cancellationToken);
                if (!registered)
                {
                    loggedIn = await TryLoginAsync(page, cancellationToken);
                }
                else
                {
                    loggedIn = true;
                }
            }

            if (!loggedIn)
            {
                await SaveFailureScreenshotAsync(page, "auth-login-failed");
                throw new InvalidOperationException(
                    "Authentication failed. Verify SIMULATION_AUTH_EMAIL/SIMULATION_AUTH_PASSWORD or use -RegisterSyntheticUser for first-time setup.");
            }

            var cookies = await ExportCookiesAsync(context);
            stopwatch.Stop();

            if (!_options.KeepBrowserOpen)
            {
                await context.DisposeAsync();
                await browser.DisposeAsync();
                playwright.Dispose();
                context = null;
                browser = null;
                playwright = null!;
            }

            return new AuthenticatedSession(
                cookies,
                RedactedIdentity.HashEmail(_options.Email),
                loginSucceeded: true,
                registered,
                stopwatch.Elapsed,
                playwright,
                browser,
                context);
        }
        catch
        {
            if (context is not null)
            {
                await context.DisposeAsync();
            }

            if (browser is not null)
            {
                await browser.DisposeAsync();
            }

            playwright?.Dispose();
            throw;
        }
    }

    private async Task<bool> TryLoginAsync(IPage page, CancellationToken cancellationToken)
    {
        await page.GotoAsync(Absolute("/Account/Login"), new PageGotoOptions { WaitUntil = WaitUntilState.DOMContentLoaded });
        cancellationToken.ThrowIfCancellationRequested();
        await page.Locator("#Input\\.Email").FillAsync(_options.Email);
        await page.Locator("#Input\\.Password").FillAsync(_options.Password);
        await page
            .GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Log in", Exact = true })
            .ClickAsync();
        await page.WaitForLoadStateAsync(LoadState.DOMContentLoaded);
        return await IsAuthenticatedViaApiAsync(page.Context, cancellationToken);
    }

    private async Task<bool> TryRegisterAsync(IPage page, CancellationToken cancellationToken)
    {
        await page.GotoAsync(Absolute("/Account/Register"), new PageGotoOptions { WaitUntil = WaitUntilState.DOMContentLoaded });
        cancellationToken.ThrowIfCancellationRequested();
        await page.Locator("#Input\\.Email").FillAsync(_options.Email);
        await page.Locator("#Input\\.Password").FillAsync(_options.Password);
        await page.Locator("#Input\\.ConfirmPassword").FillAsync(_options.Password);
        await page
            .GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Register", Exact = true })
            .ClickAsync();
        await page.WaitForLoadStateAsync(LoadState.DOMContentLoaded);
        return await IsAuthenticatedViaApiAsync(page.Context, cancellationToken);
    }

    private async Task<bool> IsAuthenticatedViaApiAsync(IBrowserContext context, CancellationToken cancellationToken)
    {
        try
        {
            var cookies = await ExportCookiesAsync(context);
            using var client = new HttpClient(HttpClientFactory.CreateHandler(_options.BaseUrl, cookies))
            {
                BaseAddress = _options.BaseUrl,
                Timeout = TimeSpan.FromMilliseconds(DefaultTimeoutMs)
            };
            client.DefaultRequestHeaders.UserAgent.ParseAdd("BooksTrafficSimulation/1.0");
            client.DefaultRequestHeaders.Accept.ParseAdd("application/json");

            using var response = await client.GetAsync("/api/books", cancellationToken);
            return response.StatusCode == HttpStatusCode.OK;
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return false;
        }
        catch (HttpRequestException)
        {
            return false;
        }
    }

    private async Task<CookieContainer> ExportCookiesAsync(IBrowserContext context)
    {
        var cookies = new CookieContainer();
        foreach (var cookie in await context.CookiesAsync())
        {
            var path = string.IsNullOrWhiteSpace(cookie.Path) ? "/" : cookie.Path;
            var domain = string.IsNullOrWhiteSpace(cookie.Domain)
                ? _options.BaseUrl.Host
                : cookie.Domain.TrimStart('.');

            var netCookie = new System.Net.Cookie(cookie.Name, cookie.Value, path, domain)
            {
                HttpOnly = cookie.HttpOnly,
                Secure = cookie.Secure
            };

            if (cookie.Expires > 0)
            {
                netCookie.Expires = DateTimeOffset.FromUnixTimeSeconds((long)cookie.Expires).UtcDateTime;
            }

            try
            {
                cookies.Add(_options.BaseUrl, netCookie);
            }
            catch (CookieException)
            {
                cookies.Add(_options.BaseUrl, new System.Net.Cookie(cookie.Name, cookie.Value, path));
            }
        }

        return cookies;
    }

    private async Task SaveFailureScreenshotAsync(IPage page, string name)
    {
        var directory = Path.Combine(_options.ArtifactRoot, "auth-failures");
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, $"{DateTimeOffset.UtcNow:yyyyMMdd-HHmmss}-{name}.png");
        await page.ScreenshotAsync(new PageScreenshotOptions { Path = path, FullPage = true });
    }

    private string Absolute(string path) =>
        new Uri(_options.BaseUrl, path).ToString();
}
