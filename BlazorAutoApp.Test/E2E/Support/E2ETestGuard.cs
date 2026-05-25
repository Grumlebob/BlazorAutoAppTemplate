using System;

namespace BlazorAutoApp.Test.E2E.Support;

public static class E2ETestGuard
{
    public static bool IsEnabled =>
        string.Equals(Environment.GetEnvironmentVariable("RUN_E2E"), "1", StringComparison.OrdinalIgnoreCase);
}
