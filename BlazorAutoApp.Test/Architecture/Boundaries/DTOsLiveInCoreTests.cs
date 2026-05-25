using System;
using System.Linq;
using Xunit;
using BlazorAutoApp.Test.Architecture.Support;

namespace BlazorAutoApp.Test.Architecture.Boundaries;

public class DTOsLiveInCoreTests
{
    [Fact]
    public void Server_Assembly_Defines_No_Public_Request_Or_Response_DTOs()
    {
        var offenders = ArchitectureAssemblies.Server.GetExportedTypes()
            .Where(t => t.IsClass && t.IsPublic)
            .Where(t => t.Name.EndsWith("Request", StringComparison.Ordinal)
                     || t.Name.EndsWith("Response", StringComparison.Ordinal))
            .Select(t => t.FullName)
            .OrderBy(n => n)
            .ToList();

        Assert.True(offenders.Count == 0,
            "Server assembly should not declare Request/Response DTOs. Found:\n" + string.Join("\n", offenders));
    }

    [Fact]
    public void Client_Assembly_Defines_No_Public_Request_Or_Response_DTOs()
    {
        var offenders = ArchitectureAssemblies.Client.GetExportedTypes()
            .Where(t => t.IsClass && t.IsPublic)
            .Where(t => t.Name.EndsWith("Request", StringComparison.Ordinal)
                     || t.Name.EndsWith("Response", StringComparison.Ordinal))
            .Select(t => t.FullName)
            .OrderBy(n => n)
            .ToList();

        Assert.True(offenders.Count == 0,
            "Client assembly should not declare Request/Response DTOs. Found:\n" + string.Join("\n", offenders));
    }

    [Fact]
    public void Core_Request_And_Response_DTOs_Live_In_UseCases()
    {
        var offenders = ArchitectureAssemblies.Core.GetExportedTypes()
            .Where(t => t.IsClass && t.IsPublic)
            .Where(t => t.Name.EndsWith("Request", StringComparison.Ordinal)
                     || t.Name.EndsWith("Response", StringComparison.Ordinal))
            .Where(t => t.Namespace is null || !t.Namespace.Contains(".UseCases.", StringComparison.Ordinal))
            .Select(t => t.FullName)
            .OrderBy(n => n)
            .ToList();

        Assert.True(offenders.Count == 0,
            "Core Request/Response DTOs should live under Features.*.UseCases.{UseCase}. Found:\n" + string.Join("\n", offenders));
    }

    [Fact]
    public void Core_Api_Interfaces_Live_In_Contracts()
    {
        var offenders = ArchitectureAssemblies.Core.GetExportedTypes()
            .Where(t => t.IsInterface && t.IsPublic && t.Name.EndsWith("Api", StringComparison.Ordinal))
            .Where(t => t.Namespace is null || !t.Namespace.EndsWith(".Contracts", StringComparison.Ordinal))
            .Select(t => t.FullName)
            .OrderBy(n => n)
            .ToList();

        Assert.True(offenders.Count == 0,
            "Core API interfaces should live under Features.*.Contracts. Found:\n" + string.Join("\n", offenders));
    }
}
