using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;
using BlazorAutoApp.Simulation.Http;
using BlazorAutoApp.Simulation.Options;
using BlazorAutoApp.Simulation.Reporting;
using BlazorAutoApp.Simulation.Scenarios;

namespace BlazorAutoApp.Simulation.Running;

internal sealed class ScenarioRunner
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    private readonly SimulationOptions _options;
    private readonly Random _random;
    private readonly ScenarioContext _context;
    private readonly IReadOnlyList<Scenario> _scenarios;
    private readonly RateLimitBudget _apiBudget;
    private readonly RateLimitBudget _healthBudget;

    public ScenarioRunner(SimulationOptions options)
    {
        _options = options;
        _random = new Random(options.Seed);
        _context = new ScenarioContext(_random);
        _scenarios = ScenarioCatalog.BuildReadOnly();
        _apiBudget = new RateLimitBudget(options.ApiRpsBudget);
        _healthBudget = new RateLimitBudget(0.2);
    }

    public async Task<SimulationReport> RunAsync(CancellationToken cancellationToken)
    {
        using var client = new HttpScenarioClient(_options.Target.BaseUrl);
        await VerifyTargetReadyAsync(client, cancellationToken);
        await DiscoverAuthorBooksAsync(client, cancellationToken);

        var startedAt = DateTimeOffset.UtcNow;
        var runId = RunId.Create(startedAt, _options.Target.Name);
        var results = new List<ScenarioRunResult>();
        var endAt = startedAt + _options.Duration;
        var requestInterval = TimeSpan.FromSeconds(1 / _options.MaxRps);
        var nextReportAt = startedAt + TimeSpan.FromSeconds(15);

        while (DateTimeOffset.UtcNow < endAt)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var loopStartedAt = DateTimeOffset.UtcNow;
            var scenario = ChooseScenario(loopStartedAt);
            if (scenario is null)
            {
                await DelayRemainingAsync(requestInterval, loopStartedAt, cancellationToken);
                continue;
            }

            var result = await RunScenarioAsync(client, scenario, cancellationToken);
            results.Add(result);

            if (DateTimeOffset.UtcNow >= nextReportAt)
            {
                PrintProgress(results, startedAt);
                nextReportAt = DateTimeOffset.UtcNow + TimeSpan.FromSeconds(15);
            }

            await DelayRemainingAsync(requestInterval, loopStartedAt, cancellationToken);
        }

        var endedAt = DateTimeOffset.UtcNow;
        return SimulationReport.Create(
            runId,
            _options,
            startedAt,
            endedAt,
            results);
    }

    private async Task VerifyTargetReadyAsync(HttpScenarioClient client, CancellationToken cancellationToken)
    {
        var ready = await client.GetAsync("/health/ready", cancellationToken);
        if (ready.StatusCode is null || (int)ready.StatusCode < 200 || (int)ready.StatusCode >= 400)
        {
            var status = ready.StatusCode?.ToString() ?? ready.Error ?? "unknown";
            throw new TargetUnavailableException($"/health/ready did not return success: {status}");
        }
    }

    private async Task DiscoverAuthorBooksAsync(HttpScenarioClient client, CancellationToken cancellationToken)
    {
        var result = await client.GetAsync("/api/author-books", cancellationToken);
        if (result.StatusCode != HttpStatusCode.OK)
        {
            return;
        }

        try
        {
            using var httpClient = new HttpClient(CreateDiscoveryHandler())
            {
                BaseAddress = _options.Target.BaseUrl,
                Timeout = TimeSpan.FromSeconds(30)
            };
            httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("BooksTrafficSimulation/1.0");

            var response = await httpClient.GetFromJsonAsync<GetAuthorBooksResponse>(
                "/api/author-books",
                JsonOptions,
                cancellationToken);

            _context.AuthorBooks = response?.Books
                .Where(static book => book.Id > 0 && !string.IsNullOrWhiteSpace(book.SeedKey))
                .ToArray() ?? [];
        }
        catch
        {
            _context.AuthorBooks = [];
        }
    }

    private HttpClientHandler CreateDiscoveryHandler()
    {
        var handler = new HttpClientHandler();
        if (_options.Target.BaseUrl.Host is "localhost" or "127.0.0.1")
        {
            handler.ServerCertificateCustomValidationCallback = HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
        }

        return handler;
    }

    private Scenario? ChooseScenario(DateTimeOffset now)
    {
        var available = _scenarios
            .Where(scenario => IsScenarioAvailable(scenario, now))
            .ToArray();

        if (available.Length == 0)
        {
            return null;
        }

        var totalWeight = available.Sum(static scenario => scenario.Weight);
        var pick = _random.Next(1, totalWeight + 1);
        foreach (var scenario in available)
        {
            pick -= scenario.Weight;
            if (pick <= 0)
            {
                MarkBudgetUsed(scenario, now);
                return scenario;
            }
        }

        MarkBudgetUsed(available[^1], now);
        return available[^1];
    }

    private bool IsScenarioAvailable(Scenario scenario, DateTimeOffset now) =>
        scenario.Category switch
        {
            ScenarioCategory.Api => _apiBudget.IsAvailable(now),
            ScenarioCategory.Health => _healthBudget.IsAvailable(now),
            _ => true
        };

    private void MarkBudgetUsed(Scenario scenario, DateTimeOffset now)
    {
        switch (scenario.Category)
        {
            case ScenarioCategory.Api:
                _apiBudget.MarkUsed(now);
                break;
            case ScenarioCategory.Health:
                _healthBudget.MarkUsed(now);
                break;
        }
    }

    private async Task<ScenarioRunResult> RunScenarioAsync(
        HttpScenarioClient client,
        Scenario scenario,
        CancellationToken cancellationToken)
    {
        var path = scenario.PathFactory(_context) ?? "/";
        var result = await client.GetAsync(path, cancellationToken);
        var rateLimited = result.StatusCode == HttpStatusCode.TooManyRequests;
        var rateLimitExpected = rateLimited && _options.AllowRateLimit;
        var expected = scenario.IsExpectedResult(result) || rateLimitExpected;

        if (rateLimited)
        {
            var retryAfter = result.RetryAfter ?? TimeSpan.FromSeconds(1);
            var now = DateTimeOffset.UtcNow;
            switch (scenario.Category)
            {
                case ScenarioCategory.Api:
                    _apiBudget.BackOff(now, retryAfter);
                    break;
                case ScenarioCategory.Health:
                    _healthBudget.BackOff(now, retryAfter);
                    break;
            }
        }

        return new ScenarioRunResult(
            scenario.Name,
            scenario.Category,
            path,
            result.StatusCode,
            expected,
            rateLimited,
            rateLimitExpected,
            result.Duration,
            result.RetryAfter,
            result.Error);
    }

    private static async Task DelayRemainingAsync(
        TimeSpan interval,
        DateTimeOffset loopStartedAt,
        CancellationToken cancellationToken)
    {
        var elapsed = DateTimeOffset.UtcNow - loopStartedAt;
        var remaining = interval - elapsed;
        if (remaining > TimeSpan.Zero)
        {
            await Task.Delay(remaining, cancellationToken);
        }
    }

    private static void PrintProgress(IReadOnlyList<ScenarioRunResult> results, DateTimeOffset startedAt)
    {
        var elapsed = DateTimeOffset.UtcNow - startedAt;
        var unexpectedFailures = results.Count(static result => !result.Expected);
        var rateLimited = results.Count(static result => result.RateLimited);
        Console.WriteLine(
            $"progress {elapsed:mm\\:ss}: requests={results.Count}, unexpected={unexpectedFailures}, 429={rateLimited}");
    }
}
