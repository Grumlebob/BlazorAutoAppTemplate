using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class FeatureSlicesArchitectureTests
{
    private static readonly string[] ResponsibilityFolders = ["Domain", "Contracts", "UseCases"];

    [Fact]
    public void CoreFeatureFiles_LiveUnder_ResponsibilityFolders()
    {
        var root = SourceSearch.GetRepoRoot();
        var featureRoot = Path.Combine(root, "BlazorAutoApp.Core", "Features");

        var offenders = Directory.EnumerateFiles(featureRoot, "*.cs", SearchOption.AllDirectories)
            .Select(file => Path.GetRelativePath(featureRoot, file))
            .Where(relative =>
            {
                var parts = relative.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                return !parts.Any(p => ResponsibilityFolders.Contains(p, StringComparer.Ordinal));
            })
            .OrderBy(x => x)
            .ToList();

        Assert.True(offenders.Count == 0,
            "Core feature files must live under Domain, Contracts, or UseCases:\n" + string.Join("\n", offenders));
    }

    [Fact]
    public void CoreUseCaseFiles_LiveUnder_NamedUseCaseFolders()
    {
        var root = SourceSearch.GetRepoRoot();
        var featureRoot = Path.Combine(root, "BlazorAutoApp.Core", "Features");

        var offenders = Directory.EnumerateFiles(featureRoot, "*.cs", SearchOption.AllDirectories)
            .Select(file => Path.GetRelativePath(featureRoot, file))
            .Where(relative =>
            {
                var parts = relative.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                var useCasesIndex = Array.IndexOf(parts, "UseCases");
                return useCasesIndex >= 0 && useCasesIndex >= parts.Length - 2;
            })
            .OrderBy(x => x)
            .ToList();

        Assert.True(offenders.Count == 0,
            "UseCases files must live under UseCases/{UseCaseName}:\n" + string.Join("\n", offenders));
    }

    [Fact]
    public void CoreFeatureNamespaces_Match_ResponsibilityFolders()
    {
        var failures = new List<string>();

        foreach (var type in ArchitectureAssemblies.Core.GetExportedTypes().Where(t => t.Namespace is not null && t.Namespace.Contains(".Features.", StringComparison.Ordinal)))
        {
            var ns = type.Namespace!;
            if (ns.Split('.').Contains("Domain", StringComparer.Ordinal) && !ns.EndsWith(".Domain", StringComparison.Ordinal))
            {
                failures.Add($"{type.FullName}: Domain types should be directly in a .Domain namespace");
            }

            if (ns.Split('.').Contains("Contracts", StringComparer.Ordinal) && !ns.EndsWith(".Contracts", StringComparison.Ordinal))
            {
                failures.Add($"{type.FullName}: Contract types should be directly in a .Contracts namespace");
            }

            if (ns.Split('.').Contains("UseCases", StringComparer.Ordinal) && !ns.Contains(".UseCases.", StringComparison.Ordinal))
            {
                failures.Add($"{type.FullName}: Use case types should be in a .UseCases.{{UseCaseName}} namespace");
            }
        }

        Assert.True(failures.Count == 0, "Core feature namespace violations:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void EachCoreRequest_HasMatchingFeatureTestClass()
    {
        var requests = ArchitectureAssemblies.Core.GetTypes()
            .Where(t => t.IsClass && t.IsPublic && t.Namespace != null && t.Namespace.Contains(".Features.") && t.Name.EndsWith("Request", StringComparison.Ordinal))
            .Select(t => new
            {
                Type = t,
                FeaturePath = GetFeaturePath(t.Namespace!),
                BaseName = t.Name[..^"Request".Length]
            })
            .Where(x => !string.IsNullOrWhiteSpace(x.FeaturePath))
            .ToList();

        Assert.NotEmpty(requests);

        var failures = new List<string>();

        foreach (var req in requests)
        {
            var expectedClass = $"{req.BaseName}Tests";
            var expectedNamespace = "BlazorAutoApp.Test.Features." + req.FeaturePath;
            var match = ArchitectureAssemblies.Tests.GetTypes()
                .FirstOrDefault(t => t.IsClass && t.IsPublic
                                     && t.Name.Equals(expectedClass, StringComparison.Ordinal)
                                     && t.Namespace is not null
                                     && t.Namespace.StartsWith(expectedNamespace, StringComparison.Ordinal));

            if (match is null)
            {
                failures.Add($"Missing test class for {req.Type.FullName}: expected {expectedNamespace}.{expectedClass}");
            }
        }

        Assert.True(failures.Count == 0, "Missing feature tests:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void FeatureTestClasses_HaveFactsOrTheories()
    {
        var featureTests = ArchitectureAssemblies.Tests.GetTypes()
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

    private static string? GetFeaturePath(string namespaceName)
    {
        const string prefix = "BlazorAutoApp.Core.Features.";
        if (!namespaceName.StartsWith(prefix, StringComparison.Ordinal))
        {
            return null;
        }

        var relative = namespaceName[prefix.Length..];
        var parts = relative.Split('.');
        var useCasesIndex = Array.IndexOf(parts, "UseCases");
        if (useCasesIndex <= 0)
        {
            return null;
        }

        return string.Join('.', parts.Take(useCasesIndex));
    }
}
