using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using BlazorAutoApp.Client.Services;
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
            bool hasServer = serverAssembly.GetTypes()
                .Any(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t));

            bool hasClient = clientAssembly.GetTypes()
                .Any(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t));

            if (!hasServer || !hasClient)
            {
                failures.Add($"{api.FullName}: server={hasServer}, client={hasClient}");
            }
        }

        Assert.True(failures.Count == 0, "Missing implementations:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void Implementations_FollowServiceNamingConvention()
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

            // Only enforce naming if implementations exist; the other test checks presence
            if (serverImpls.Any() && !serverImpls.Any(t => t.Name.EndsWith("ServerService", StringComparison.Ordinal)))
            {
                failures.Add($"{api.FullName}: server implementations must end with 'ServerService' (found: {string.Join(", ", serverImpls.Select(x => x.Name))})");
            }

            if (clientImpls.Any() && !clientImpls.Any(t => t.Name.EndsWith("ClientService", StringComparison.Ordinal)))
            {
                failures.Add($"{api.FullName}: client implementations must end with 'ClientService' (found: {string.Join(", ", clientImpls.Select(x => x.Name))})");
            }
        }

        Assert.True(failures.Count == 0, "Naming convention violations:\n" + string.Join("\n", failures));
    }
}
