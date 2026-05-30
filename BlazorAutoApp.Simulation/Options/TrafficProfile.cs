namespace BlazorAutoApp.Simulation.Options;

internal sealed record TrafficProfile(
    string Name,
    TimeSpan DefaultDuration,
    int DefaultUsers,
    bool RequiresBurstGate)
{
    public static bool TryCreate(string name, out TrafficProfile? profile, out string error)
    {
        error = "";
        profile = name.Trim().ToLowerInvariant() switch
        {
            "smoke" => new TrafficProfile("smoke", TimeSpan.FromSeconds(90), 1, false),
            "demo" => new TrafficProfile("demo", TimeSpan.FromMinutes(10), 4, false),
            "soak-lite" => new TrafficProfile("soak-lite", TimeSpan.FromMinutes(30), 2, false),
            "burst" => new TrafficProfile("burst", TimeSpan.FromSeconds(45), 10, true),
            _ => null
        };

        if (profile is null)
        {
            error = $"unknown profile '{name}'";
            return false;
        }

        return true;
    }

    public double DefaultMaxRps(string target) =>
        Name switch
        {
            "smoke" => 1,
            "demo" => IsDeployed(target) ? 2 : 3,
            "soak-lite" => IsDeployed(target) ? 1 : 2,
            "burst" => IsDeployed(target) ? 2 : 10,
            _ => 1
        };

    public double DefaultApiRpsBudget(string target) =>
        Name switch
        {
            "smoke" => 0.5,
            "demo" => IsDeployed(target) ? 0.5 : 0.8,
            "soak-lite" => IsDeployed(target) ? 0.3 : 0.5,
            "burst" => IsDeployed(target) ? 0.5 : 1,
            _ => 0.5
        };

    public double DefaultAuthWriteRpsBudget(string target) =>
        Name switch
        {
            "demo" => IsDeployed(target) ? 0.1 : 0.2,
            "soak-lite" => IsDeployed(target) ? 0.05 : 0.1,
            _ => 0.1
        };

    private static bool IsDeployed(string target) =>
        target is "localcluster-public" or "cloud-public";
}
