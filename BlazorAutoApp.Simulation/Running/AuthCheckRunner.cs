using BlazorAutoApp.Simulation.Auth;
using BlazorAutoApp.Simulation.Books;
using BlazorAutoApp.Simulation.Options;
using BlazorAutoApp.Simulation.Reporting;
using BlazorAutoApp.Simulation.Scenarios;

namespace BlazorAutoApp.Simulation.Running;

internal sealed class AuthCheckRunner
{
    private readonly SimulationOptions _options;

    public AuthCheckRunner(SimulationOptions options)
    {
        _options = options;
    }

    public async Task<SimulationReport> RunAsync(CancellationToken cancellationToken)
    {
        using var readinessClient = new Http.HttpScenarioClient(_options.Target.BaseUrl);
        var ready = await readinessClient.GetAsync("/health/ready", cancellationToken);
        if (ready.StatusCode is null || (int)ready.StatusCode < 200 || (int)ready.StatusCode >= 400)
        {
            var status = ready.StatusCode?.ToString() ?? ready.Error ?? "unknown";
            throw new TargetUnavailableException($"/health/ready did not return success: {status}");
        }

        var startedAt = DateTimeOffset.UtcNow;
        var runId = RunId.Create(startedAt, _options.Target.Name);
        var results = new List<ScenarioRunResult>();

        await using var session = await new BrowserAuthBootstrap(
            AuthBootstrapOptions.From(_options, keepBrowserOpen: false)).BootstrapAsync(cancellationToken);

        using var books = new AuthenticatedBooksClient(_options.Target.BaseUrl, session.Cookies);
        var list = await books.ListAsync("authenticated_book_list", cancellationToken);
        results.Add(books.ToScenarioResult(list, ScenarioCategory.AuthenticatedApi));

        var endedAt = DateTimeOffset.UtcNow;
        var auth = new AuthReport(
            Enabled: true,
            Mode: session.RegisteredUser ? "browser-register" : "browser-login",
            Target: _options.Target.Name,
            EmailHash: session.EmailHash,
            LoginSucceeded: session.LoginSucceeded,
            RegisteredUser: session.RegisteredUser,
            BootstrapDurationMs: session.BootstrapDuration.TotalMilliseconds,
            AuthenticatedApiCheckSucceeded: list.Expected);

        return SimulationReport.Create(
            runId,
            _options,
            startedAt,
            endedAt,
            results,
            auth);
    }
}
