namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class HeadRequestExtensions
{
    public static IEndpointRouteBuilder MapPublicPageHeadRequests(this IEndpointRouteBuilder endpoints)
    {
        MapHead(endpoints, "/");
        MapHead(endpoints, "/books");
        MapHead(endpoints, "/books/author/{seedKey}");
        MapHead(endpoints, "/books/design-demos");
        MapHead(endpoints, "/books/design-demos/{designId}");
        MapHead(endpoints, "/Account/Login");

        return endpoints;
    }

    private static void MapHead(IEndpointRouteBuilder endpoints, string pattern) =>
        endpoints.MapMethods(pattern, [HttpMethods.Head], () => Results.Ok())
            .ExcludeFromDescription();
}
