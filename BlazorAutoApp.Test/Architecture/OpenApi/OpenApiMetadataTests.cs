using System.Text.Json;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Frontend.OpenApi;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.AspNetCore.TestHost;
using StackExchange.Redis;
using Xunit;

namespace BlazorAutoApp.Test.Architecture.OpenApi;

public sealed class OpenApiMetadataTests
{
    [Fact]
    public async Task Metadata_host_describes_real_book_endpoints_without_application_infrastructure()
    {
        var builder = OpenApiMetadataHosting.CreateBuilder();
        builder.WebHost.UseTestServer();

        Assert.DoesNotContain(builder.Configuration.Sources, source =>
            source.GetType().Name is "JsonConfigurationSource" or "UserSecretsConfigurationSource");
        Assert.DoesNotContain(builder.Services, descriptor =>
            descriptor.ServiceType == typeof(AppDbContext)
            || descriptor.ServiceType == typeof(IConnectionMultiplexer)
            || descriptor.ServiceType == typeof(UserManager<ApplicationUser>)
            || descriptor.ServiceType == typeof(IEmailSender<ApplicationUser>));

        await using var app = builder.Build();
        app.UseAuthorization();
        app.UseRateLimiter();
        OpenApiMetadataHosting.MapEndpoints(app);

        await app.StartAsync();
        try
        {
            using var response = await app.GetTestClient().GetAsync("/openapi/v1.json");
            response.EnsureSuccessStatusCode();

            using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            var root = document.RootElement;
            Assert.StartsWith("3.1.", root.GetProperty("openapi").GetString(), StringComparison.Ordinal);

            var paths = root.GetProperty("paths");
            var authorBooksList = GetOperation(paths, "/api/author-books", "get");
            Assert.True(authorBooksList.GetProperty("responses").TryGetProperty("200", out _));
            Assert.True(authorBooksList.GetProperty("responses").TryGetProperty("429", out _));
            Assert.False(authorBooksList.TryGetProperty("security", out _));

            var authorBooksItem = GetOperation(paths, "/api/author-books/{id}", "get");
            Assert.True(authorBooksItem.GetProperty("responses").TryGetProperty("404", out _));
            Assert.Equal(
                "#/components/schemas/GetAuthorBookResponse",
                GetJsonSchemaReference(authorBooksItem, "200"));

            var privateBooksList = GetOperation(paths, "/api/books", "get");
            var privateResponses = privateBooksList.GetProperty("responses");
            Assert.True(privateResponses.TryGetProperty("401", out _));
            Assert.True(privateResponses.TryGetProperty("403", out _));
            Assert.True(privateResponses.TryGetProperty("429", out _));
            Assert.Contains(
                privateBooksList.GetProperty("security").EnumerateArray(),
                requirement => requirement.TryGetProperty("IdentityApplicationCookie", out _));

            var privateBookItem = GetOperation(paths, "/api/books/{id}", "get");
            Assert.True(privateBookItem.GetProperty("responses").TryGetProperty("404", out _));

            var createBook = GetOperation(paths, "/api/books", "post");
            var createResponses = createBook.GetProperty("responses");
            Assert.True(createResponses.TryGetProperty("201", out _));
            Assert.True(createResponses.TryGetProperty("400", out _));
            Assert.True(createResponses.TryGetProperty("401", out _));
            Assert.True(createResponses.TryGetProperty("403", out _));

            var securityScheme = root.GetProperty("components")
                .GetProperty("securitySchemes")
                .GetProperty("IdentityApplicationCookie");
            Assert.Equal("apiKey", securityScheme.GetProperty("type").GetString());
            Assert.Equal("cookie", securityScheme.GetProperty("in").GetString());
            Assert.Equal(".AspNetCore.Identity.Application", securityScheme.GetProperty("name").GetString());

            Assert.Equal(
                "#/components/schemas/GetAuthorBooksResponse",
                GetJsonSchemaReference(authorBooksList, "200"));

            var authorBooksSchema = root.GetProperty("components")
                .GetProperty("schemas")
                .GetProperty("GetAuthorBooksResponse");
            Assert.True(authorBooksSchema.GetProperty("properties")
                .TryGetProperty("books", out var booksProperty));
            Assert.Equal(
                "#/components/schemas/AuthorBookListItemResponse",
                booksProperty.GetProperty("items").GetProperty("$ref").GetString());

            var authorBookProperties = root.GetProperty("components")
                .GetProperty("schemas")
                .GetProperty("AuthorBookListItemResponse")
                .GetProperty("properties");
            Assert.Contains("id", authorBookProperties.EnumerateObject().Select(property => property.Name));
            Assert.Contains("seedKey", authorBookProperties.EnumerateObject().Select(property => property.Name));
            Assert.Contains("title", authorBookProperties.EnumerateObject().Select(property => property.Name));
            Assert.Contains("author", authorBookProperties.EnumerateObject().Select(property => property.Name));
            Assert.Contains("url", authorBookProperties.EnumerateObject().Select(property => property.Name));
            Assert.Contains(
                "null",
                authorBookProperties.GetProperty("author").GetProperty("type")
                    .EnumerateArray()
                    .Select(value => value.GetString()));
        }
        finally
        {
            await app.StopAsync();
        }
    }

    private static JsonElement GetOperation(JsonElement paths, string expectedPath, string method)
    {
        var path = paths.EnumerateObject().Single(property =>
            string.Equals(property.Name.TrimEnd('/'), expectedPath.TrimEnd('/'), StringComparison.Ordinal));
        return path.Value.GetProperty(method);
    }

    private static string? GetJsonSchemaReference(JsonElement operation, string statusCode) =>
        operation.GetProperty("responses")
            .GetProperty(statusCode)
            .GetProperty("content")
            .GetProperty("application/json")
            .GetProperty("schema")
            .GetProperty("$ref")
            .GetString();
}
