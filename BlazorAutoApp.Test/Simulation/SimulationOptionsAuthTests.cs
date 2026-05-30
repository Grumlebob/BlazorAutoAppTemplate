using System.Collections;
using BlazorAutoApp.Simulation.Options;
using Xunit;

namespace BlazorAutoApp.Test.Simulation;

public sealed class SimulationOptionsAuthTests
{
    [Fact]
    public void LocalAuthCheckUsesSeededUserWhenCredentialsAreNotProvided()
    {
        var result = SimulationOptions.Parse(["--target", "local", "--auth-check"], EmptyEnvironment());

        Assert.Empty(result.Errors);
        Assert.NotNull(result.Options);
        Assert.True(result.Options.AuthCheck);
        Assert.Equal("user@user.com", result.Options.AuthEmail);
        Assert.Equal("User123", result.Options.AuthPassword);
    }

    [Fact]
    public void WritesRequireWriteGate()
    {
        var result = SimulationOptions.Parse(["--target", "local", "--writes"], EmptyEnvironment());

        Assert.Contains(result.Errors, error => error.Contains("--allow-write", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void CleanupOnlyRequiresWriteGate()
    {
        var result = SimulationOptions.Parse(["--target", "local", "--cleanup-only"], EmptyEnvironment());

        Assert.Contains(result.Errors, error => error.Contains("--allow-write", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void DeployedWritesRequireDeployedAndWriteGates()
    {
        var result = SimulationOptions.Parse(["--target", "cloud-public", "--writes"], EmptyEnvironment());

        Assert.Contains(result.Errors, error => error.Contains("--allow-deployed", StringComparison.OrdinalIgnoreCase));
        Assert.Contains(result.Errors, error => error.Contains("--allow-write", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void KeepSyntheticDataRequiresExplicitYes()
    {
        var env = EnvironmentWith(("SIMULATION_ALLOW_WRITE", "1"));
        var result = SimulationOptions.Parse(["--target", "local", "--writes", "--keep-synthetic-data"], env);

        Assert.Contains(result.Errors, error => error.Contains("--keep-synthetic-data", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void PlainAuthPasswordOptionIsRejected()
    {
        var result = SimulationOptions.Parse(["--target", "local", "--auth-check", "--auth-password", "secret"], EmptyEnvironment());

        Assert.Contains(result.Errors, error => error.Contains("do not pass auth passwords", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void BrowserSamplerRequiresWrites()
    {
        var result = SimulationOptions.Parse(["--target", "local", "--auth-check", "--browser-sampler"], EmptyEnvironment());

        Assert.Contains(result.Errors, error => error.Contains("--browser-sampler requires --writes", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void LocalCustomAuthEmailRequiresPassword()
    {
        var result = SimulationOptions.Parse(["--target", "local", "--auth-check", "--auth-email", "custom@example.com"], EmptyEnvironment());

        Assert.Contains(result.Errors, error => error.Contains("SIMULATION_AUTH_PASSWORD", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void RegisterSyntheticUserRequiresWriteGate()
    {
        var result = SimulationOptions.Parse(["--target", "local", "--auth-check", "--register-synthetic-user"], EmptyEnvironment());

        Assert.Contains(result.Errors, error => error.Contains("--allow-write", StringComparison.OrdinalIgnoreCase));
    }

    private static IDictionary EmptyEnvironment() =>
        new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);

    private static IDictionary EnvironmentWith(params (string Key, string Value)[] values) =>
        values.ToDictionary(static item => item.Key, static item => (string?)item.Value, StringComparer.OrdinalIgnoreCase);
}
