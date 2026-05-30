using BlazorAutoApp.Simulation.Options;

namespace BlazorAutoApp.Simulation.Auth;

internal sealed record AuthBootstrapOptions(
    Uri BaseUrl,
    string Email,
    string Password,
    bool RegisterSyntheticUser,
    bool KeepBrowserOpen,
    bool HeadedBrowser,
    string ArtifactRoot)
{
    public static AuthBootstrapOptions From(SimulationOptions options, bool keepBrowserOpen) =>
        new(
            options.Target.BaseUrl,
            options.AuthEmail ?? throw new InvalidOperationException("Auth email was not resolved."),
            options.AuthPassword ?? throw new InvalidOperationException("Auth password was not resolved."),
            options.RegisterSyntheticUser,
            keepBrowserOpen,
            options.HeadedBrowser,
            options.ReportDirectory);
}
