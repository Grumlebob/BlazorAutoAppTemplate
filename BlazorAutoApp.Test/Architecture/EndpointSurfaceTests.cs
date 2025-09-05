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
public class EndpointSurfaceTests
{
    private readonly IServiceProvider _services;

    public EndpointSurfaceTests(WebAppFactory factory)
    {
        _services = factory.Services;
    }

    [Fact]
    public void MoviesEndpoints_Exist_With_Expected_Routes()
    {
        var dataSource = _services.GetRequiredService<EndpointDataSource>();
        var endpoints = dataSource.Endpoints.OfType<RouteEndpoint>().ToList();

        bool Has(string method, params string[] patterns)
        {
            return endpoints.Any(e =>
            {
                var httpMethods = e.Metadata.OfType<Microsoft.AspNetCore.Routing.HttpMethodMetadata>().FirstOrDefault()?.HttpMethods;
                if (httpMethods is null || !httpMethods.Contains(method, StringComparer.OrdinalIgnoreCase)) return false;
                var raw = e.RoutePattern.RawText ?? string.Empty;
                return patterns.Any(p => string.Equals(raw, p, StringComparison.Ordinal))
                    || patterns.Any(p => string.Equals(raw.TrimEnd('/'), p.TrimEnd('/'), StringComparison.Ordinal));
            });
        }

        Assert.True(Has("GET", "/api/movies/", "/api/movies"));
        Assert.True(Has("GET", "/api/movies/{id:int}"));
        Assert.True(Has("POST", "/api/movies/", "/api/movies"));
        Assert.True(Has("PUT", "/api/movies/{id:int}"));
        Assert.True(Has("DELETE", "/api/movies/{id:int}"));
    }
}

