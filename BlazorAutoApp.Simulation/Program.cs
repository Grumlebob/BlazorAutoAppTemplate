using System.Globalization;
using BlazorAutoApp.Simulation.Auth;
using BlazorAutoApp.Simulation.Options;
using BlazorAutoApp.Simulation.Reporting;
using BlazorAutoApp.Simulation.Running;

namespace BlazorAutoApp.Simulation;

internal static class Program
{
    public static async Task<int> Main(string[] args)
    {
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;

        if (args.Any(static arg => string.Equals(arg, "--help", StringComparison.OrdinalIgnoreCase)
            || string.Equals(arg, "-h", StringComparison.OrdinalIgnoreCase)
            || string.Equals(arg, "/?", StringComparison.OrdinalIgnoreCase)))
        {
            HelpText.Write();
            return ExitCodes.Success;
        }

        var parseResult = SimulationOptions.Parse(args, Environment.GetEnvironmentVariables());
        if (parseResult.Errors.Count > 0)
        {
            foreach (var error in parseResult.Errors)
            {
                Console.Error.WriteLine($"error: {error}");
            }

            Console.Error.WriteLine();
            HelpText.WriteShort();
            return ExitCodes.InvalidOptions;
        }

        var options = parseResult.Options!;

        if (options.InstallBrowsers)
        {
            return PlaywrightInstaller.InstallChromium();
        }

        using var cancellation = new CancellationTokenSource();
        Console.CancelKeyPress += (_, eventArgs) =>
        {
            eventArgs.Cancel = true;
            cancellation.Cancel();
            Console.Error.WriteLine("Cancellation requested; stopping simulation...");
        };

        if (options.AuthEnabled)
        {
            PrintResolvedPlan(options);
            var authRunner = options.AuthCheck && !options.Writes && !options.CleanupOnly
                ? new AuthCheckRunner(options)
                : null;
            SimulationReport authReport;
            try
            {
                authReport = authRunner is not null
                    ? await authRunner.RunAsync(cancellation.Token)
                    : await new AuthenticatedScenarioRunner(options).RunAsync(cancellation.Token);
            }
            catch (TargetUnavailableException ex)
            {
                Console.Error.WriteLine($"target unavailable: {ex.Message}");
                return ExitCodes.TargetUnavailable;
            }
            catch (OperationCanceledException)
            {
                Console.Error.WriteLine("simulation cancelled");
                return ExitCodes.UnexpectedRuntimeError;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"authenticated simulation failed: {ex.Message}");
                return ExitCodes.UnexpectedRuntimeError;
            }

            var authReportPaths = await SimulationReportWriter.WriteAsync(authReport, options.ReportDirectory);
            Console.WriteLine();
            Console.WriteLine(authReport.ToConsoleSummary(authReportPaths.MarkdownPath));

            if (authReport.Writes.CleanupAttempted && !authReport.Writes.CleanupSucceeded)
            {
                return ExitCodes.CleanupFailed;
            }

            return authReport.FailedThresholds ? ExitCodes.ThresholdFailure : ExitCodes.Success;
        }

        PrintResolvedPlan(options);

        var runner = new ScenarioRunner(options);
        SimulationReport report;
        try
        {
            report = await runner.RunAsync(cancellation.Token);
        }
        catch (TargetUnavailableException ex)
        {
            Console.Error.WriteLine($"target unavailable: {ex.Message}");
            return ExitCodes.TargetUnavailable;
        }
        catch (OperationCanceledException)
        {
            Console.Error.WriteLine("simulation cancelled");
            return ExitCodes.UnexpectedRuntimeError;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"simulation failed: {ex.Message}");
            return ExitCodes.UnexpectedRuntimeError;
        }

        var reportPaths = await SimulationReportWriter.WriteAsync(report, options.ReportDirectory);
        Console.WriteLine();
        Console.WriteLine(report.ToConsoleSummary(reportPaths.MarkdownPath));

        return report.FailedThresholds
            ? ExitCodes.ThresholdFailure
            : ExitCodes.Success;
    }

    private static void PrintResolvedPlan(SimulationOptions options)
    {
        Console.WriteLine("Traffic simulation");
        Console.WriteLine($"  target                  {options.Target.Name}");
        Console.WriteLine($"  base URL                {options.Target.BaseUrl}");
        Console.WriteLine($"  profile                 {options.Profile.Name}");
        Console.WriteLine($"  duration                {FormatDuration(options.Duration)}");
        Console.WriteLine($"  max RPS                 {options.MaxRps:0.###}");
        Console.WriteLine($"  API budget              {options.ApiRpsBudget:0.###} rps");
        Console.WriteLine($"  auth write budget       {options.AuthWriteRpsBudget:0.###} rps");
        Console.WriteLine($"  virtual users           {options.VirtualUsers}");
        Console.WriteLine($"  auth check              {(options.AuthCheck ? "enabled" : "disabled")}");
        Console.WriteLine($"  auth identity           {(options.AuthEnabled ? "configured" : "not used")}");
        Console.WriteLine($"  writes                  {(options.Writes ? "enabled" : "disabled")}");
        Console.WriteLine($"  browser sampler         {(options.BrowserSampler ? "enabled" : "disabled")}");
        Console.WriteLine($"  allow rate limit        {(options.AllowRateLimit ? "yes" : "no")}");
        Console.WriteLine($"  report directory        {options.ReportDirectory}");
        Console.WriteLine();
    }

    private static string FormatDuration(TimeSpan value)
    {
        if (value.TotalSeconds < 60)
        {
            return $"{value.TotalSeconds:0}s";
        }

        if (value.TotalMinutes < 60)
        {
            return $"{value.TotalMinutes:0.#}m";
        }

        return $"{value.TotalHours:0.#}h";
    }
}

internal static class ExitCodes
{
    public const int Success = 0;
    public const int ThresholdFailure = 1;
    public const int InvalidOptions = 2;
    public const int TargetUnavailable = 3;
    public const int CleanupFailed = 4;
    public const int UnexpectedRuntimeError = 5;
}
