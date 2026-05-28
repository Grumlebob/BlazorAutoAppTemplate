using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Client.Features.Books.AuthorBookcase;
using BlazorAutoApp.Features.Books.Caching;
using BlazorAutoApp.Features.Books.Endpoints;
using BlazorAutoApp.Features.Books.AuthorBookcase.Seed;
using BlazorAutoApp.Features.Books.Services;

namespace BlazorAutoApp.Features.Books;

public static class DependencyInjection
{
    public static IServiceCollection AddBooksFeature(this IServiceCollection services, IConfiguration config)
    {
        services.AddHttpContextAccessor();
        services.AddScoped<ICurrentUserAccessor, CurrentUserAccessor>();
        services.AddScoped<IBooksApi, BooksServerService>();
        services.AddScoped<IAuthorBooksApi, AuthorBooksServerService>();
        services.AddScoped<IAuthorBookSeeder, AuthorBookSeeder>();
        services.AddScoped<AuthorBookcaseState>();
        services.Configure<BooksCacheOptions>(config.GetSection("Cache:Books"));
        return services;
    }

    public static IEndpointRouteBuilder MapBooksFeature(this IEndpointRouteBuilder routes)
    {
        routes.MapBookEndpoints();
        routes.MapAuthorBookEndpoints();
        return routes;
    }
}
