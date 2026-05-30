using System.Net;
using Microsoft.Playwright;

namespace BlazorAutoApp.Simulation.Auth;

internal sealed class AuthenticatedSession : IAsyncDisposable
{
    public AuthenticatedSession(
        CookieContainer cookies,
        string emailHash,
        bool loginSucceeded,
        bool registeredUser,
        TimeSpan bootstrapDuration,
        IPlaywright? playwright,
        IBrowser? browser,
        IBrowserContext? browserContext)
    {
        Cookies = cookies;
        EmailHash = emailHash;
        LoginSucceeded = loginSucceeded;
        RegisteredUser = registeredUser;
        BootstrapDuration = bootstrapDuration;
        Playwright = playwright;
        Browser = browser;
        BrowserContext = browserContext;
    }

    public CookieContainer Cookies { get; }

    public string EmailHash { get; }

    public bool LoginSucceeded { get; }

    public bool RegisteredUser { get; }

    public TimeSpan BootstrapDuration { get; }

    public IPlaywright? Playwright { get; }

    public IBrowser? Browser { get; }

    public IBrowserContext? BrowserContext { get; }

    public async ValueTask DisposeAsync()
    {
        if (BrowserContext is not null)
        {
            await BrowserContext.DisposeAsync();
        }

        if (Browser is not null)
        {
            await Browser.DisposeAsync();
        }

        Playwright?.Dispose();
    }
}
