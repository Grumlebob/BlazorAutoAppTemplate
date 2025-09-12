using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Xunit;
using BlazorAutoApp.Test.TestingSetup;

namespace BlazorAutoApp.Test.Architecture;

public class FeatureSlicesArchitectureTests
{
    [Fact]
    public void EachCoreRequest_HasMatchingFeatureTestClass()
    {
        var core = typeof(BlazorAutoApp.Core.Features.Movies.IMoviesApi).Assembly;
        var tests = typeof(WebAppFactory).Assembly;

        // Find all request DTOs in Core under Features
        var requests = core.GetTypes()
            .Where(t => t.IsClass && t.IsPublic && t.Namespace != null && t.Namespace.Contains(".Features.") && t.Name.EndsWith("Request", StringComparison.Ordinal))
            .Select(t => new
            {
                Type = t,
                Feature = t.Namespace!.Split('.').SkipWhile(s => s != "Features").Skip(1).FirstOrDefault(),
                BaseName = t.Name[..^"Request".Length]
            })
            .Where(x => !string.IsNullOrWhiteSpace(x.Feature))
            .ToList();

        Assert.NotEmpty(requests);

        var failures = new List<string>();

        foreach (var req in requests)
        {
            var expectedClass = $"{req.BaseName}Tests";
            // Allow nested feature folders in tests (e.g., Features/Inspections/HullImages)
            var match = tests.GetTypes()
                .FirstOrDefault(t => t.IsClass && t.IsPublic
                                     && t.Name.Equals(expectedClass, StringComparison.Ordinal)
                                     && t.Namespace is not null
                                     && t.Namespace.StartsWith("BlazorAutoApp.Test.Features.", StringComparison.Ordinal)
                                     && t.Namespace.Split('.').Contains(req.Feature));

            if (match is null)
            {
                failures.Add($"Missing test class for {req.Type.FullName}: expected a class named {expectedClass} under a namespace containing '.{req.Feature}' within BlazorAutoApp.Test.Features.*");
            }
        }

        Assert.True(failures.Count == 0, "Missing feature tests:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void FeatureTestClasses_HaveFactsOrTheories()
    {
        var tests = typeof(WebAppFactory).Assembly;
        var featureTests = tests.GetTypes()
            .Where(t => t.IsClass && t.IsPublic && t.Namespace != null && t.Namespace.StartsWith("BlazorAutoApp.Test.Features.", StringComparison.Ordinal) && t.Name.EndsWith("Tests", StringComparison.Ordinal))
            .ToList();

        Assert.NotEmpty(featureTests);

        var failures = new List<string>();

        foreach (var t in featureTests)
        {
            var hasTestMethod = t.GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.DeclaredOnly)
                .Any(m => m.GetCustomAttributes(inherit: true).Any(a => a.GetType().Name is "FactAttribute" or "TheoryAttribute"));

            if (!hasTestMethod)
            {
                failures.Add($"{t.FullName} should contain at least one [Fact] or [Theory] method");
            }
        }

        Assert.True(failures.Count == 0, "Feature test classes missing test methods:\n" + string.Join("\n", failures));
    }
}
