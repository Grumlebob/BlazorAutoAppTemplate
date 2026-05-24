using System;
using System.Collections.Generic;
using System.Linq;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

[Collection("MediaTestCollection")]
public class DiWiringTests(WebAppFactory factory)
{
    private readonly IServiceProvider _services = factory.Services;

    [Fact]
    public void Core_Api_Interfaces_Resolve_To_Server_Implementations()
    {
        var apiInterfaces = ArchitectureAssemblies.Core.GetTypes()
            .Where(t => t.IsInterface && t.IsPublic && t.Name.EndsWith("Api", StringComparison.Ordinal))
            .ToList();

        Assert.NotEmpty(apiInterfaces);

        var failures = new List<string>();

        using var scope = _services.CreateScope();
        foreach (var api in apiInterfaces)
        {
            var serverImpls = ArchitectureAssemblies.Server.GetTypes()
                .Where(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t))
                .ToList();

            if (serverImpls.Count != 1)
            {
                failures.Add($"{api.FullName}: expected exactly one server implementation, found {serverImpls.Count}");
                continue;
            }

            var svc = scope.ServiceProvider.GetService(api);
            if (svc is null)
            {
                failures.Add($"{api.FullName}: not registered in DI");
                continue;
            }

            if (svc.GetType() != serverImpls[0])
            {
                failures.Add($"{api.FullName}: resolved {svc.GetType().FullName}, expected {serverImpls[0].FullName}");
            }
        }

        Assert.True(failures.Count == 0, "DI wiring violations:\n" + string.Join("\n", failures));
    }
}
