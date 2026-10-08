using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using Xunit;
using BlazorAutoApp.Test.Architecture.Support;

namespace BlazorAutoApp.Test.Architecture.Slices;

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
    public void ClientRouteComponents_LiveInside_FeatureRouteSlices()
    {
        var root = SourceSearch.GetRepoRoot();
        var rootPagesFolder = Path.Combine(root, "BlazorAutoApp.Client", "Pages");
        var featurePagesFolders = Directory
            .EnumerateDirectories(Path.Combine(root, "BlazorAutoApp.Client", "Features"), "Pages", SearchOption.AllDirectories)
            .OrderBy(path => path)
            .ToList();

        Assert.False(Directory.Exists(rootPagesFolder),
            "Client routable components must live under feature Routes folders, not a root Pages folder.");
        Assert.True(featurePagesFolders.Count == 0,
            "Client route folders should be named Routes, not Pages:\n" + string.Join("\n", featurePagesFolders));
    }

    [Fact]
    public void CoreFeaturesWithUseCases_HaveFeatureTestCoverage()
    {
        var featureNames = ArchitectureAssemblies.Core.GetTypes()
            .Where(t => t.IsPublic
                && t.Namespace is not null
                && t.Namespace.StartsWith("BlazorAutoApp.Core.Features.", StringComparison.Ordinal)
                && t.Namespace.Contains(".UseCases.", StringComparison.Ordinal))
            .Select(t => GetFeatureName(t.Namespace!))
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Distinct(StringComparer.Ordinal)
            .OrderBy(name => name, StringComparer.Ordinal)
            .ToList();

        Assert.NotEmpty(featureNames);

        var testTypes = ArchitectureAssemblies.Tests.GetTypes()
            .Where(t => t.IsClass
                && t.IsPublic
                && t.Namespace is not null
                && t.Namespace.StartsWith("BlazorAutoApp.Test.Features.", StringComparison.Ordinal)
                && t.GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.DeclaredOnly)
                    .Any(m => m.GetCustomAttributes(inherit: true)
                        .Any(a => a.GetType().Name is "FactAttribute" or "TheoryAttribute")))
            .ToList();

        var failures = featureNames
            .Where(featureName => !testTypes.Any(testType =>
            {
                var expectedNamespace = "BlazorAutoApp.Test.Features." + featureName;
                return testType.Namespace!.StartsWith(expectedNamespace, StringComparison.Ordinal);
            }))
            .Select(featureName => $"Missing feature test coverage for BlazorAutoApp.Core.Features.{featureName}")
            .ToList();

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

    [Fact]
    public void PassiveRequestDtoConstructionTests_AreNotAllowed()
    {
        var root = SourceSearch.GetRepoRoot();
        var testRoot = Path.Combine(root, "BlazorAutoApp.Test", "Features");
        var passiveTestNamePattern = new Regex(
            @"\b(?<name>(?:Request_(?:CanBeCreated|Has[A-Za-z0-9_]*)|CanBeCreated))\b",
            RegexOptions.Compiled);

        var offenders = Directory.EnumerateFiles(testRoot, "*Tests.cs", SearchOption.AllDirectories)
            .SelectMany(file =>
            {
                var relative = Path.GetRelativePath(root, file);
                return File.ReadLines(file)
                    .Select((line, index) => new { Line = line, LineNumber = index + 1 })
                    .Where(row => passiveTestNamePattern.IsMatch(row.Line))
                    .Select(row => $"{relative}:{row.LineNumber}: {row.Line.Trim()}");
            })
            .OrderBy(x => x, StringComparer.Ordinal)
            .ToList();

        Assert.True(offenders.Count == 0,
            "Do not test passive DTO construction; test validation, API behavior, mapper behavior, or persistence instead:\n"
            + string.Join("\n", offenders));
    }

    private static string? GetFeatureName(string namespaceName)
    {
        const string prefix = "BlazorAutoApp.Core.Features.";
        if (!namespaceName.StartsWith(prefix, StringComparison.Ordinal))
        {
            return null;
        }

        var relative = namespaceName[prefix.Length..];
        return relative.Split('.').FirstOrDefault();
    }
}
