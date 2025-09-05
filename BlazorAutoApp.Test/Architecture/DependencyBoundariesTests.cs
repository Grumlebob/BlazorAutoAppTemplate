using System;
using System.Linq;
using BlazorAutoApp.Client.Services;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Features.Movies;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class DependencyBoundariesTests
{
    [Fact]
    public void Core_DoesNotReference_AspNetCore_Or_EFCore()
    {
        var core = typeof(IMoviesApi).Assembly;
        var refs = core.GetReferencedAssemblies().Select(a => a.Name!).ToList();

        Assert.DoesNotContain(refs, n => n.StartsWith("Microsoft.AspNetCore", StringComparison.Ordinal));
        Assert.DoesNotContain(refs, n => n.StartsWith("Microsoft.EntityFrameworkCore", StringComparison.Ordinal));
        Assert.DoesNotContain(refs, n => n.StartsWith("Npgsql", StringComparison.Ordinal));
    }
    
    [Fact]
    public void Client_DoesNotReference_EFCore_Or_Npgsql()
    {
        var client = typeof(MoviesClientService).Assembly;
        var refs = client.GetReferencedAssemblies().Select(a => a.Name!).ToList();

        Assert.DoesNotContain(refs, n => n.StartsWith("Microsoft.EntityFrameworkCore", StringComparison.Ordinal));
        Assert.DoesNotContain(refs, n => n.StartsWith("Npgsql", StringComparison.Ordinal));
    }

    [Fact]
    public void Client_References_Core_And_Not_Server()
    {
        var client = typeof(MoviesClientService).Assembly;
        var refs = client.GetReferencedAssemblies().Select(a => a.Name!).ToList();

        Assert.Contains(refs, n => n.Equals("BlazorAutoApp.Core", StringComparison.Ordinal));
        Assert.DoesNotContain(refs, n => n.Equals("BlazorAutoApp", StringComparison.Ordinal));
    }
}

