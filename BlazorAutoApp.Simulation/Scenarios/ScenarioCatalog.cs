using System.Net;
using BlazorAutoApp.Simulation.Http;

namespace BlazorAutoApp.Simulation.Scenarios;

internal static class ScenarioCatalog
{
    public static IReadOnlyList<Scenario> BuildReadOnly()
    {
        return
        [
            new("home", ScenarioCategory.Page, 15, _ => "/", IsSuccess),
            new("books-page", ScenarioCategory.Page, 10, _ => "/books", IsSuccess),
            new("author-page", ScenarioCategory.Page, 15, ctx => $"/books/author/{ctx.NextAuthorSeedKey()}", IsSuccess),
            new("design-demos", ScenarioCategory.Page, 6, _ => "/books/design-demos", IsSuccess),
            new("design-demo-detail", ScenarioCategory.Page, 4, ctx => $"/books/design-demos/{ctx.NextDesignId()}", IsSuccess),
            new("login-page", ScenarioCategory.Page, 5, _ => "/Account/Login", IsSuccess),
            new("register-page", ScenarioCategory.Page, 5, _ => "/Account/Register", IsSuccess),
            new("expected-page-not-found", ScenarioCategory.Page, 5, _ => "/simulation-not-found", IsExpectedNotFound),
            new("author-books-list-api", ScenarioCategory.Api, 15, _ => "/api/author-books", IsSuccess),
            new("author-book-detail-api", ScenarioCategory.Api, 15, ctx => $"/api/author-books/{ctx.NextAuthorBookId()}", IsSuccess),
            new("expected-api-not-found", ScenarioCategory.Api, 5, _ => "/api/author-books/2147483647", IsExpectedNotFound),
            new("health-ready", ScenarioCategory.Health, 3, _ => "/health/ready", IsSuccess),
            new("health-live", ScenarioCategory.Health, 2, _ => "/health/live", IsSuccess)
        ];
    }

    private static bool IsSuccess(HttpResult result) =>
        result.StatusCode is >= HttpStatusCode.OK and < HttpStatusCode.BadRequest;

    private static bool IsExpectedNotFound(HttpResult result) =>
        result.StatusCode == HttpStatusCode.NotFound;
}
