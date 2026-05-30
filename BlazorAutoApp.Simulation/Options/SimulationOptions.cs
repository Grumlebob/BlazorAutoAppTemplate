using System.Collections;
using System.Globalization;

namespace BlazorAutoApp.Simulation.Options;

internal sealed record SimulationOptions
{
    public required TargetProfile Target { get; init; }

    public required TrafficProfile Profile { get; init; }

    public required TimeSpan Duration { get; init; }

    public required double MaxRps { get; init; }

    public required double ApiRpsBudget { get; init; }

    public required double AuthWriteRpsBudget { get; init; }

    public required int VirtualUsers { get; init; }

    public required int Seed { get; init; }

    public required string ReportDirectory { get; init; }

    public required bool AuthCheck { get; init; }

    public required string? AuthEmail { get; init; }

    public required string AuthPasswordEnvironmentVariable { get; init; }

    public required string? AuthPassword { get; init; }

    public required bool RegisterSyntheticUser { get; init; }

    public required bool KeepSyntheticData { get; init; }

    public required bool InstallBrowsers { get; init; }

    public required string PlaywrightBrowser { get; init; }

    public required bool HeadedBrowser { get; init; }

    public required bool Writes { get; init; }

    public required bool Cleanup { get; init; }

    public required bool CleanupOnly { get; init; }

    public required bool BrowserSampler { get; init; }

    public required bool AllowRateLimit { get; init; }

    public required bool AllowDeployed { get; init; }

    public required bool AllowWrite { get; init; }

    public required bool AllowBurst { get; init; }

    public required bool Yes { get; init; }

    public required bool FailOn5xx { get; init; }

    public bool AuthEnabled =>
        AuthCheck || Writes || Cleanup || CleanupOnly || BrowserSampler || RegisterSyntheticUser;

    public static ParseResult Parse(string[] args, IDictionary environment)
    {
        var raw = CommandLineReader.Read(args);
        var errors = new List<string>();

        var targetName = raw.Get("target") ?? GetEnvironment(environment, "SIMULATION_TARGET") ?? "local";
        var profileName = raw.Get("profile") ?? GetEnvironment(environment, "SIMULATION_PROFILE") ?? "smoke";

        if (!TargetProfile.TryCreate(targetName, raw.Get("base-url") ?? GetEnvironment(environment, "SIMULATION_BASE_URL"), out var target, out var targetError))
        {
            errors.Add(targetError);
        }

        if (!TrafficProfile.TryCreate(profileName, out var profile, out var profileError))
        {
            errors.Add(profileError);
        }

        var allowDeployed = raw.Has("allow-deployed") || IsEnabled(environment, "SIMULATION_ALLOW_DEPLOYED");
        var allowWrite = raw.Has("allow-write") || IsEnabled(environment, "SIMULATION_ALLOW_WRITE");
        var allowBurst = raw.Has("allow-burst") || IsEnabled(environment, "SIMULATION_ALLOW_BURST");
        var yes = raw.Has("yes");

        if (target is not null && target.RequiresDeployedGate && !allowDeployed)
        {
            errors.Add($"target '{target.Name}' requires --allow-deployed or SIMULATION_ALLOW_DEPLOYED=1");
        }

        if (profile is not null && profile.RequiresBurstGate && !allowBurst)
        {
            errors.Add("profile 'burst' requires --allow-burst or SIMULATION_ALLOW_BURST=1");
        }

        if (!TryReadDuration(raw.Get("duration") ?? GetEnvironment(environment, "SIMULATION_DURATION"), profile?.DefaultDuration ?? TimeSpan.FromSeconds(90), out var duration, out var durationError))
        {
            errors.Add(durationError);
        }

        var maxRps = ReadDouble(raw.Get("max-rps") ?? GetEnvironment(environment, "SIMULATION_MAX_RPS"), profile?.DefaultMaxRps(target?.Name ?? "local") ?? 1, "max-rps", errors);
        var apiRpsBudget = ReadDouble(raw.Get("api-rps-budget") ?? GetEnvironment(environment, "SIMULATION_API_RPS_BUDGET"), profile?.DefaultApiRpsBudget(target?.Name ?? "local") ?? 0.5, "api-rps-budget", errors);
        var authWriteRpsBudget = ReadDouble(raw.Get("auth-write-rps-budget") ?? GetEnvironment(environment, "SIMULATION_AUTH_WRITE_RPS_BUDGET"), profile?.DefaultAuthWriteRpsBudget(target?.Name ?? "local") ?? 0.1, "auth-write-rps-budget", errors);
        var users = ReadInt(raw.Get("users"), profile?.DefaultUsers ?? 1, "users", errors);
        var seed = ReadInt(raw.Get("seed"), Random.Shared.Next(), "seed", errors);
        var reportDirectory = raw.Get("report-dir") ?? GetEnvironment(environment, "SIMULATION_REPORT_DIR") ?? Path.Combine("artifacts", "simulation");
        var authCheck = raw.Has("auth-check");
        var writes = raw.Has("writes");
        var cleanup = raw.Has("cleanup");
        var cleanupOnly = raw.Has("cleanup-only");
        var browserSampler = raw.Has("browser-sampler");
        var registerSyntheticUser = raw.Has("register-synthetic-user");
        var keepSyntheticData = raw.Has("keep-synthetic-data");
        var installBrowsers = raw.Has("install-browsers");
        var headedBrowser = raw.Has("headed-browser");
        var authPasswordEnvironmentVariable = raw.Get("auth-password-env") ?? "SIMULATION_AUTH_PASSWORD";
        var configuredAuthEmail = raw.Get("auth-email") ?? GetEnvironment(environment, "SIMULATION_AUTH_EMAIL");
        var configuredAuthPassword = GetEnvironment(environment, authPasswordEnvironmentVariable);
        var authEmail = configuredAuthEmail;
        var authPassword = configuredAuthPassword;
        var playwrightBrowser = (raw.Get("playwright-browser") ?? "chromium").Trim().ToLowerInvariant();
        var authEnabled = authCheck || writes || cleanup || cleanupOnly || browserSampler || registerSyntheticUser;

        if (raw.Has("auth-password"))
        {
            errors.Add("do not pass auth passwords on the command line; use --auth-password-env or SIMULATION_AUTH_PASSWORD");
        }

        if (maxRps <= 0)
        {
            errors.Add("--max-rps must be greater than 0");
        }

        if (apiRpsBudget < 0)
        {
            errors.Add("--api-rps-budget must be 0 or greater");
        }

        if (authWriteRpsBudget < 0)
        {
            errors.Add("--auth-write-rps-budget must be 0 or greater");
        }

        if (users <= 0)
        {
            errors.Add("--users must be greater than 0");
        }

        if (authPasswordEnvironmentVariable.Length == 0)
        {
            errors.Add("--auth-password-env must not be empty");
        }

        if (playwrightBrowser != "chromium")
        {
            errors.Add("--playwright-browser currently supports only 'chromium'");
        }

        if ((writes || cleanup || cleanupOnly || registerSyntheticUser) && !allowWrite)
        {
            errors.Add("writes, cleanup, and registration require --allow-write or SIMULATION_ALLOW_WRITE=1");
        }

        if (keepSyntheticData && (!writes || !allowWrite || !yes))
        {
            errors.Add("--keep-synthetic-data requires --writes, --allow-write, and --yes");
        }

        if (browserSampler && !writes)
        {
            errors.Add("--browser-sampler requires --writes");
        }

        if (target is not null
            && target.Name == "origin-via-tunnel"
            && (writes || cleanup || cleanupOnly || registerSyntheticUser)
            && !allowDeployed
            && !IsLocalhost(target.BaseUrl))
        {
            errors.Add("origin-via-tunnel authenticated writes require --allow-deployed unless --base-url is local");
        }

        if (authEnabled)
        {
            var defaultLocalCredentialsAllowed = target?.Name == "local"
                && authPasswordEnvironmentVariable == "SIMULATION_AUTH_PASSWORD"
                && string.IsNullOrWhiteSpace(configuredAuthEmail)
                && string.IsNullOrWhiteSpace(configuredAuthPassword);

            if (defaultLocalCredentialsAllowed)
            {
                authEmail = "user@user.com";
                authPassword = "User123";
            }

            if (string.IsNullOrWhiteSpace(authEmail))
            {
                errors.Add("authenticated simulation requires --auth-email or SIMULATION_AUTH_EMAIL");
            }

            if (string.IsNullOrWhiteSpace(authPassword))
            {
                errors.Add($"authenticated simulation requires password environment variable {authPasswordEnvironmentVariable}");
            }
        }

        if (errors.Count > 0 || target is null || profile is null)
        {
            return new ParseResult(null, errors);
        }

        var allowRateLimit = raw.Has("allow-rate-limit") || profile.Name == "burst";
        return new ParseResult(new SimulationOptions
        {
            Target = target,
            Profile = profile,
            Duration = duration,
            MaxRps = maxRps,
            ApiRpsBudget = Math.Min(apiRpsBudget, maxRps),
            AuthWriteRpsBudget = Math.Min(authWriteRpsBudget, maxRps),
            VirtualUsers = users,
            Seed = seed,
            ReportDirectory = reportDirectory,
            AuthCheck = authCheck,
            AuthEmail = authEmail,
            AuthPasswordEnvironmentVariable = authPasswordEnvironmentVariable,
            AuthPassword = authPassword,
            RegisterSyntheticUser = registerSyntheticUser,
            KeepSyntheticData = keepSyntheticData,
            InstallBrowsers = installBrowsers,
            PlaywrightBrowser = playwrightBrowser,
            HeadedBrowser = headedBrowser,
            Writes = writes,
            Cleanup = cleanup,
            CleanupOnly = cleanupOnly,
            BrowserSampler = browserSampler,
            AllowRateLimit = allowRateLimit,
            AllowDeployed = allowDeployed,
            AllowWrite = allowWrite,
            AllowBurst = allowBurst,
            Yes = yes,
            FailOn5xx = raw.Has("fail-on-5xx") || profile.Name == "smoke"
        }, []);
    }

    private static bool TryReadDuration(string? raw, TimeSpan fallback, out TimeSpan value, out string error)
    {
        error = "";
        if (string.IsNullOrWhiteSpace(raw))
        {
            value = fallback;
            return true;
        }

        raw = raw.Trim();
        var suffix = raw[^1];
        var numberText = char.IsLetter(suffix) ? raw[..^1] : raw;
        if (!double.TryParse(numberText, NumberStyles.Float, CultureInfo.InvariantCulture, out var number) || number <= 0)
        {
            value = fallback;
            error = $"invalid duration '{raw}'";
            return false;
        }

        value = char.ToLowerInvariant(suffix) switch
        {
            's' => TimeSpan.FromSeconds(number),
            'm' => TimeSpan.FromMinutes(number),
            'h' => TimeSpan.FromHours(number),
            _ when !char.IsLetter(suffix) => TimeSpan.FromSeconds(number),
            _ => fallback
        };

        if (value == fallback && char.IsLetter(suffix) && suffix is not ('s' or 'S' or 'm' or 'M' or 'h' or 'H'))
        {
            error = $"invalid duration suffix in '{raw}'";
            return false;
        }

        return true;
    }

    private static double ReadDouble(string? raw, double fallback, string name, ICollection<string> errors)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return fallback;
        }

        if (double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value))
        {
            return value;
        }

        errors.Add($"--{name} must be a number");
        return fallback;
    }

    private static int ReadInt(string? raw, int fallback, string name, ICollection<string> errors)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return fallback;
        }

        if (int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value))
        {
            return value;
        }

        errors.Add($"--{name} must be an integer");
        return fallback;
    }

    private static string? GetEnvironment(IDictionary environment, string name) =>
        environment[name] as string;

    private static bool IsEnabled(IDictionary environment, string name)
    {
        var value = GetEnvironment(environment, name);
        return string.Equals(value, "1", StringComparison.OrdinalIgnoreCase)
            || string.Equals(value, "true", StringComparison.OrdinalIgnoreCase)
            || string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsLocalhost(Uri uri) =>
        string.Equals(uri.Host, "localhost", StringComparison.OrdinalIgnoreCase)
        || string.Equals(uri.Host, "127.0.0.1", StringComparison.OrdinalIgnoreCase)
        || string.Equals(uri.Host, "::1", StringComparison.OrdinalIgnoreCase);
}
