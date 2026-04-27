using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using BlazorAutoApp.Client.Features.Movies;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Features.Movies;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class ArchitectureTests
{
    [Fact]
    public void ForEachCoreApiInterface_HasServerAndClientImplementation()
    {
        // Assemblies
        var coreAssembly = typeof(IMoviesApi).Assembly;
        var serverAssembly = typeof(MoviesServerService).Assembly;
        var clientAssembly = typeof(MoviesClientService).Assembly;

        // Convention: public interfaces in Core ending with 'Api'
        var apiInterfaces = coreAssembly.GetTypes()
            .Where(t => t.IsInterface && t.IsPublic && t.Name.EndsWith("Api", StringComparison.Ordinal))
            .ToList();

        Assert.NotEmpty(apiInterfaces);

        var failures = new List<string>();

        foreach (var api in apiInterfaces)
        {
            var serverCount = serverAssembly.GetTypes()
                .Count(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t));
            var clientCount = clientAssembly.GetTypes()
                .Count(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t));

            if (serverCount != 1 || clientCount != 1)
            {
                var root = SourceSearch.GetRepoRoot();
                var apiHint = string.Join("\n", SourceSearch.FindTypeHints(root, "BlazorAutoApp.Core", api));
                var hintBlock = string.IsNullOrWhiteSpace(apiHint) ? string.Empty : $"\n  > {apiHint.Replace("\n", "\n  > ")}";
                failures.Add($"{api.FullName}: expected exactly 1 server and 1 client implementation, found server={serverCount}, client={clientCount}{hintBlock}");
            }
        }

        Assert.True(failures.Count == 0, "Implementation count violations:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void Implementations_LiveIn_FeatureNamespaces()
    {
        var coreAssembly = typeof(IMoviesApi).Assembly;
        var serverAssembly = typeof(MoviesServerService).Assembly;
        var clientAssembly = typeof(MoviesClientService).Assembly;

        var apiInterfaces = coreAssembly.GetTypes()
            .Where(t => t.IsInterface && t.IsPublic && t.Name.EndsWith("Api", StringComparison.Ordinal))
            .ToList();

        Assert.NotEmpty(apiInterfaces);

        var failures = new List<string>();

        foreach (var api in apiInterfaces)
        {
            var serverImpls = serverAssembly.GetTypes()
                .Where(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t))
                .ToList();

            var clientImpls = clientAssembly.GetTypes()
                .Where(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t))
                .ToList();

            if (serverImpls.Any(t => t.Namespace is null || !t.Namespace.StartsWith("BlazorAutoApp.Features.", StringComparison.Ordinal)))
            {
                var root = SourceSearch.GetRepoRoot();
                var hints = serverImpls.SelectMany(t => SourceSearch.FindTypeHints(root, "BlazorAutoApp", t));
                failures.Add($"{api.FullName}: server implementations must live under BlazorAutoApp.Features.* (found: {string.Join(", ", serverImpls.Select(x => x.FullName))})\n  > " + string.Join("\n  > ", hints));
            }

            if (clientImpls.Any(t => t.Namespace is null || !t.Namespace.StartsWith("BlazorAutoApp.Client.Features.", StringComparison.Ordinal)))
            {
                var root = SourceSearch.GetRepoRoot();
                var hints = clientImpls.SelectMany(t => SourceSearch.FindTypeHints(root, "BlazorAutoApp.Client", t));
                failures.Add($"{api.FullName}: client implementations must live under BlazorAutoApp.Client.Features.* (found: {string.Join(", ", clientImpls.Select(x => x.FullName))})\n  > " + string.Join("\n  > ", hints));
            }
        }

        Assert.True(failures.Count == 0, "Feature namespace violations:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void ClientAssembly_HasNo_ServiceNamespace()
    {
        var clientAssembly = typeof(MoviesClientService).Assembly;
        var offenders = clientAssembly.GetTypes()
            .Where(t => t.Namespace is not null && t.Namespace.StartsWith("BlazorAutoApp.Client.Services", StringComparison.Ordinal))
            .Select(t => t.FullName)
            .OrderBy(x => x)
            .ToList();

        Assert.True(offenders.Count == 0, "Client service namespace is not allowed:\n" + string.Join("\n", offenders));
    }
}
