using System;
using System.Collections.Generic;
using System.Linq;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.AspNetCore.Routing;
using Microsoft.AspNetCore.Routing.Patterns;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

[Collection("MediaTestCollection")]
public class EndpointSurfaceTests(WebAppFactory factory)
{
    private readonly IServiceProvider _services = factory.Services;

    [Fact]
    public void MoviesEndpoints_Exist_With_Expected_Routes()
    {
        var endpoints = RouteEndpoints();

        Assert.True(Has(endpoints, "GET", "/api/movies/", "/api/movies"));
        Assert.True(Has(endpoints, "GET", "/api/movies/{id:int}"));
        Assert.True(Has(endpoints, "POST", "/api/movies/", "/api/movies"));
        Assert.True(Has(endpoints, "PUT", "/api/movies/{id:int}"));
        Assert.True(Has(endpoints, "DELETE", "/api/movies/{id:int}"));
    }

    [Fact]
    public void IdentityShowcaseEndpoints_Exist_With_Expected_Routes()
    {
        var endpoints = RouteEndpoints();

        Assert.True(Has(endpoints, "GET", "/api/identity-showcase/public"));
        Assert.True(Has(endpoints, "GET", "/api/identity-showcase/secure"));
        Assert.True(Has(endpoints, "GET", "/api/identity-showcase/admin-probe"));
    }

    private List<RouteEndpoint> RouteEndpoints()
    {
        var dataSource = _services.GetRequiredService<EndpointDataSource>();
        return dataSource.Endpoints.OfType<RouteEndpoint>().ToList();
    }

    private static bool Has(List<RouteEndpoint> endpoints, string method, params string[] patterns)
    {
        return endpoints.Any(e =>
        {
            var httpMethods = e.Metadata.OfType<HttpMethodMetadata>().FirstOrDefault()?.HttpMethods;
            if (httpMethods is null || !httpMethods.Contains(method, StringComparer.OrdinalIgnoreCase)) return false;
            var raw = Normalize(e.RoutePattern.RawText ?? string.Empty);
            return patterns.Any(p => string.Equals(raw, Normalize(p), StringComparison.Ordinal));
        });
    }

    private static string Normalize(string pattern)
    {
        return pattern.Trim('/');
    }
}
