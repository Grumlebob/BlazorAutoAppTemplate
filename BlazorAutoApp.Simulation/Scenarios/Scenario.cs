using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;
using BlazorAutoApp.Simulation.Http;

namespace BlazorAutoApp.Simulation.Scenarios;

internal enum ScenarioCategory
{
    Page,
    Api,
    Health,
    AuthenticatedApi,
    AuthenticatedWrite,
    Browser
}

internal sealed record Scenario(
    string Name,
    ScenarioCategory Category,
    int Weight,
    Func<ScenarioContext, string?> PathFactory,
    Func<HttpResult, bool> IsExpectedResult);

internal sealed class ScenarioContext
{
    public ScenarioContext(Random random)
    {
        Random = random;
    }

    public Random Random { get; }

    public IReadOnlyList<AuthorBookListItemResponse> AuthorBooks { get; set; } = [];

    public string NextAuthorSeedKey() =>
        AuthorBooks.Count == 0
            ? "traceback"
            : AuthorBooks[Random.Next(AuthorBooks.Count)].SeedKey;

    public int NextAuthorBookId() =>
        AuthorBooks.Count == 0
            ? 1
            : AuthorBooks[Random.Next(AuthorBooks.Count)].Id;

    public string NextDesignId()
    {
        string[] designIds =
        [
            "cloth-hardback",
            "decorative-hardcover",
            "field-notebook",
            "prism-atlas",
            "droplet-monograph",
            "transit-map-folio",
            "compass-fieldbook",
            "atlas-pinboard",
            "seismograph-log",
            "alpine-trail-guide"
        ];

        return designIds[Random.Next(designIds.Length)];
    }
}
