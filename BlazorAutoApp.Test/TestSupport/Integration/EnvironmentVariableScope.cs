using System;
using System.Collections.Generic;

namespace BlazorAutoApp.Test.TestSupport.Integration;

internal sealed class EnvironmentVariableScope : IDisposable
{
    private readonly Dictionary<string, string?> _previousValues = [];

    public EnvironmentVariableScope(IReadOnlyDictionary<string, string?> values)
    {
        foreach (var (key, value) in values)
        {
            _previousValues[key] = Environment.GetEnvironmentVariable(key);
            Environment.SetEnvironmentVariable(key, value);
        }
    }

    public void Dispose()
    {
        foreach (var (key, value) in _previousValues)
        {
            Environment.SetEnvironmentVariable(key, value);
        }
    }
}
