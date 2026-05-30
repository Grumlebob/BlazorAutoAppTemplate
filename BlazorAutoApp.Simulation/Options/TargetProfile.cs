namespace BlazorAutoApp.Simulation.Options;

internal sealed record TargetProfile(string Name, Uri BaseUrl, bool RequiresDeployedGate)
{
    public static bool TryCreate(string name, string? baseUrlOverride, out TargetProfile? profile, out string error)
    {
        error = "";
        name = name.Trim().ToLowerInvariant();

        var defaultUrl = name switch
        {
            "local" => "https://localhost:7186",
            "localcluster-public" => "https://books.jacobgrum.com",
            "cloud-public" => "https://bookscloud.jacobgrum.com",
            "origin-via-tunnel" => null,
            _ => "__unknown__"
        };

        if (defaultUrl == "__unknown__")
        {
            profile = null;
            error = $"unknown target '{name}'";
            return false;
        }

        if (defaultUrl is null && string.IsNullOrWhiteSpace(baseUrlOverride))
        {
            profile = null;
            error = "target 'origin-via-tunnel' requires --base-url";
            return false;
        }

        var url = baseUrlOverride ?? defaultUrl!;
        if (!Uri.TryCreate(url, UriKind.Absolute, out var baseUrl))
        {
            profile = null;
            error = $"invalid base URL '{url}'";
            return false;
        }

        profile = new TargetProfile(name, baseUrl, name is "localcluster-public" or "cloud-public");
        return true;
    }
}
