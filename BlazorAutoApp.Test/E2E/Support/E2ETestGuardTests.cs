using System.Collections.Generic;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.E2E.Support;

[Collection(TestCollectionNames.E2E)]
public sealed class E2ETestGuardTests
{
    [Fact]
    public void IsEnabled_RequiresRunE2EFlag()
    {
        using var _ = NewScope(("RUN_E2E", null));

        Assert.False(E2ETestGuard.IsEnabled);

        using var enabled = NewScope(("RUN_E2E", "1"));

        Assert.True(E2ETestGuard.IsEnabled);
    }

    [Fact]
    public void ObservabilityGuard_RequiresRunE2EAndObservabilityFlag()
    {
        using var _ = NewScope(
            ("RUN_E2E", null),
            ("RUN_OBSERVABILITY_E2E", "1"));

        Assert.False(E2ETestGuard.IsObservabilityEnabled);

        using var enabled = NewScope(("RUN_E2E", "1"));

        Assert.True(E2ETestGuard.IsObservabilityEnabled);

        using var observabilityOff = NewScope(("RUN_OBSERVABILITY_E2E", null));

        Assert.False(E2ETestGuard.IsObservabilityEnabled);
    }

    private static EnvironmentVariableScope NewScope(params (string Key, string? Value)[] values)
    {
        var variables = new Dictionary<string, string?>();
        foreach (var (key, value) in values)
        {
            variables[key] = value;
        }

        return new EnvironmentVariableScope(variables);
    }
}
