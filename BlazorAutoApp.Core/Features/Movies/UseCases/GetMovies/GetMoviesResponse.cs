using BlazorAutoApp.Core.Features.Movies.Domain;

namespace BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;

public class GetMoviesResponse
{
    public required List<Movie> Movies { get; init; }
}
