using BlazorAutoApp.Core.Features.Movies;

namespace BlazorAutoApp.Features.Movies;

public static class Composition
{
    public static IServiceCollection AddMoviesFeature(this IServiceCollection services, IConfiguration config)
    {
        services.AddScoped<IMoviesApi, MoviesServerService>();
        services.Configure<MoviesCacheOptions>(config.GetSection("Cache:Movies"));
        return services;
    }

    public static IEndpointRouteBuilder MapMoviesFeature(this IEndpointRouteBuilder routes)
    {
        routes.MapMovieEndpoints();
        return routes;
    }
}
