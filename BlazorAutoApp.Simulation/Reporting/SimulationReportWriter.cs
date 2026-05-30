using System.Text;
using System.Text.Json;

namespace BlazorAutoApp.Simulation.Reporting;

internal static class SimulationReportWriter
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true
    };

    public static async Task<ReportPaths> WriteAsync(SimulationReport report, string reportRoot)
    {
        var directoryName = $"{report.StartedAtUtc:yyyyMMdd-HHmmss}-{report.Target}-{report.Profile}";
        var directory = Path.Combine(reportRoot, directoryName);
        Directory.CreateDirectory(directory);

        var jsonPath = Path.Combine(directory, "summary.json");
        var markdownPath = Path.Combine(directory, "summary.md");
        var ledgerPath = Path.Combine(directory, "synthetic-ledger.json");

        await File.WriteAllTextAsync(jsonPath, JsonSerializer.Serialize(report, JsonOptions), Encoding.UTF8);
        await File.WriteAllTextAsync(markdownPath, ToMarkdown(report), Encoding.UTF8);
        if (report.SyntheticBooks.Count > 0)
        {
            await File.WriteAllTextAsync(ledgerPath, JsonSerializer.Serialize(report.SyntheticBooks, JsonOptions), Encoding.UTF8);
        }

        return new ReportPaths(jsonPath, markdownPath);
    }

    private static string ToMarkdown(SimulationReport report)
    {
        var builder = new StringBuilder();
        builder.AppendLine("# Traffic Simulation Summary");
        builder.AppendLine();
        builder.AppendLine($"target: {report.Target}");
        builder.AppendLine($"profile: {report.Profile}");
        builder.AppendLine($"base URL: {report.BaseUrl}");
        builder.AppendLine($"duration: {report.DurationSeconds:0.#}s");
        builder.AppendLine($"requests: {report.RequestCount}");
        builder.AppendLine($"p50: {report.Latency.P50Ms:0.#} ms");
        builder.AppendLine($"p95: {report.Latency.P95Ms:0.#} ms");
        builder.AppendLine($"p99: {report.Latency.P99Ms:0.#} ms");
        builder.AppendLine($"api budget: {report.ApiRpsBudget:0.###} rps");
        builder.AppendLine($"unexpected 429: {report.RateLimit.Unexpected429}");
        builder.AppendLine($"auth: {(report.Auth.Enabled ? report.Auth.Mode : "disabled")}");
        if (report.Auth.Enabled)
        {
            builder.AppendLine($"auth email hash: {report.Auth.EmailHash}");
            builder.AppendLine($"auth API check: {(report.Auth.AuthenticatedApiCheckSucceeded ? "ok" : "failed")}");
            builder.AppendLine($"registered user: {(report.Auth.RegisteredUser ? "yes" : "no")}");
        }

        builder.AppendLine($"writes: {(report.WritesEnabled ? "enabled" : "disabled")}");
        builder.AppendLine($"created: {report.Writes.Created}");
        builder.AppendLine($"updated: {report.Writes.Updated}");
        builder.AppendLine($"deleted: {report.Writes.Deleted}");
        builder.AppendLine($"cleanup: {report.Writes.CleanupStatus}");
        builder.AppendLine($"browser sampler: {(report.BrowserSamplerEnabled ? "enabled" : "disabled")}");
        if (report.BrowserSampler.Enabled)
        {
            builder.AppendLine($"browser journeys: {report.BrowserSampler.JourneysSucceeded}/{report.BrowserSampler.JourneysStarted} succeeded");
        }

        builder.AppendLine("Grafana range: last 15 minutes");
        builder.AppendLine();
        builder.AppendLine("## Status Codes");
        builder.AppendLine();
        foreach (var item in report.StatusCodes.OrderBy(static pair => pair.Key, StringComparer.Ordinal))
        {
            builder.AppendLine($"- {item.Key}: {item.Value}");
        }

        builder.AppendLine();
        builder.AppendLine("## Scenarios");
        builder.AppendLine();
        foreach (var scenario in report.Scenarios)
        {
            builder.AppendLine($"- {scenario.Name}: {scenario.Count} requests, {scenario.Unexpected} unexpected, p95 {scenario.Latency.P95Ms:0.#} ms");
        }

        if (report.Errors.Count > 0)
        {
            builder.AppendLine();
            builder.AppendLine("## Errors");
            builder.AppendLine();
            foreach (var error in report.Errors)
            {
                builder.AppendLine($"- {error}");
            }
        }

        return builder.ToString();
    }
}

internal sealed record ReportPaths(string JsonPath, string MarkdownPath);
