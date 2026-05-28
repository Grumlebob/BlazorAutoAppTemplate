using System;
using System.Collections.Generic;
using System.Linq;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Routing;
using Microsoft.AspNetCore.Routing.Patterns;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Architecture.Endpoints;

[Collection("IntegrationTestCollection")]
public class EndpointSurfaceTests(WebAppFactory factory)
{
    private readonly IServiceProvider _services = factory.Services;

    [Fact]
    public void BooksEndpoints_Exist_With_Expected_Routes()
    {
        var endpoints = RouteEndpoints();

        Assert.True(Has(endpoints, "GET", "ListBooks", "/api/books/", "/api/books"));
        Assert.True(Has(endpoints, "GET", "GetBook", "/api/books/{id:int}"));
        Assert.True(Has(endpoints, "POST", "CreateBook", "/api/books/", "/api/books"));
        Assert.True(Has(endpoints, "PUT", "UpdateBook", "/api/books/{id:int}"));
        Assert.True(Has(endpoints, "DELETE", "DeleteBook", "/api/books/{id:int}"));
        Assert.True(Has(endpoints, "GET", "ListAuthorBooks", "/api/author-books/", "/api/author-books"));
        Assert.True(Has(endpoints, "GET", "GetAuthorBook", "/api/author-books/{id:int}"));
    }

    private List<RouteEndpoint> RouteEndpoints()
    {
        var dataSource = _services.GetRequiredService<EndpointDataSource>();
        return dataSource.Endpoints.OfType<RouteEndpoint>().ToList();
    }

    private static bool Has(List<RouteEndpoint> endpoints, string method, string endpointName, params string[] patterns)
    {
        return endpoints.Any(e =>
        {
            var httpMethods = e.Metadata.OfType<HttpMethodMetadata>().FirstOrDefault()?.HttpMethods;
            if (httpMethods is null || !httpMethods.Contains(method, StringComparer.OrdinalIgnoreCase)) return false;
            var name = e.Metadata.OfType<IEndpointNameMetadata>().FirstOrDefault()?.EndpointName;
            if (!string.Equals(name, endpointName, StringComparison.Ordinal)) return false;
            var raw = Normalize(e.RoutePattern.RawText ?? string.Empty);
            return patterns.Any(p => string.Equals(raw, Normalize(p), StringComparison.Ordinal));
        });
    }

    private static string Normalize(string pattern)
    {
        return pattern.Trim('/');
    }
}
