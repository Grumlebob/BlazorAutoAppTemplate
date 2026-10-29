using GrumPlates.Core.Features.Books.Contracts;
using GrumPlates.Features.Books.AuthorBookcase.Seed;
using GrumPlates.Features.Books.Caching;
using GrumPlates.Features.Books.Endpoints;
using GrumPlates.Features.Books.Services;

namespace GrumPlates.Features.Books;

public static class DependencyInjection
{
    public static IServiceCollection AddBooksFeature(this IServiceCollection services, IConfiguration config)
    {
        services.AddScoped<IBooksApi, BooksServerService>();
        services.AddScoped<IAuthorBooksApi, AuthorBooksServerService>();
        services.AddScoped<IAuthorBookSeeder, AuthorBookSeeder>();
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
