using System;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Features.Movies;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

[Collection("MediaTestCollection")]
public class DiWiringTests(WebAppFactory factory)
{
    private readonly IServiceProvider _services = factory.Services;

    [Fact]
    public void IMoviesApi_Resolves_To_ServerService()
    {
        using var scope = _services.CreateScope();
        var svc = scope.ServiceProvider.GetRequiredService<IMoviesApi>();
        Assert.IsType<MoviesServerService>(svc);
    }
}

