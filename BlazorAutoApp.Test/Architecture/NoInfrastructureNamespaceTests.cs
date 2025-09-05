using System;
using System.Linq;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class NoInfrastructureNamespaceTests
{
    [Fact]
    public void ServerAssembly_HasNo_Infrastructure_Namespace()
    {
        var server = typeof(BlazorAutoApp.Features.Movies.MoviesServerService).Assembly;
        var offending = server.GetTypes()
            .Where(t => t.Namespace != null && t.Namespace.Split('.').Contains("Infrastructure", StringComparer.Ordinal))
            .Select(t => t.FullName)
            .ToList();

        Assert.True(offending.Count == 0, "Found types under an Infrastructure namespace:\n" + string.Join("\n", offending));
    }

    [Fact]
    public void ClientAssembly_HasNo_Infrastructure_Namespace()
    {
        var client = typeof(BlazorAutoApp.Client.Services.MoviesClientService).Assembly;
        var offending = client.GetTypes()
            .Where(t => t.Namespace != null && t.Namespace.Split('.').Contains("Infrastructure", StringComparer.Ordinal))
            .Select(t => t.FullName)
            .ToList();

        Assert.True(offending.Count == 0, "Found types under an Infrastructure namespace in client:\n" + string.Join("\n", offending));
    }

    [Fact]
    public void CoreAssembly_HasNo_Infrastructure_Namespace()
    {
        var core = typeof(BlazorAutoApp.Core.Features.Movies.IMoviesApi).Assembly;
        var offending = core.GetTypes()
            .Where(t => t.Namespace != null && t.Namespace.Split('.').Contains("Infrastructure", StringComparer.Ordinal))
            .Select(t => t.FullName)
            .ToList();

        Assert.True(offending.Count == 0, "Found types under an Infrastructure namespace in core:\n" + string.Join("\n", offending));
    }
}

