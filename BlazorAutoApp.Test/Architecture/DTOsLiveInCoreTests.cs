using System;
using System.Linq;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class DTOsLiveInCoreTests
{
    [Fact]
    public void Server_Assembly_Defines_No_Public_Request_Or_Response_DTOs()
    {
        var asm = typeof(Program).Assembly; // Server
        var offenders = asm.GetExportedTypes()
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
        var asm = typeof(BlazorAutoApp.Client._Imports).Assembly; // Client
        var offenders = asm.GetExportedTypes()
            .Where(t => t.IsClass && t.IsPublic)
            .Where(t => t.Name.EndsWith("Request", StringComparison.Ordinal)
                     || t.Name.EndsWith("Response", StringComparison.Ordinal))
            .Select(t => t.FullName)
            .OrderBy(n => n)
            .ToList();

        Assert.True(offenders.Count == 0,
            "Client assembly should not declare Request/Response DTOs. Found:\n" + string.Join("\n", offenders));
    }
}

