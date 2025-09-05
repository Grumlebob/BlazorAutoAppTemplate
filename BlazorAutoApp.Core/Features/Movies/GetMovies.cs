namespace BlazorAutoApp.Core.Features.Movies;

public class GetMoviesRequest
{
}

public class GetMoviesResponse
{
    public required List<Movie> Movies { get; init; }
}

