namespace BlazorAutoApp.Core.Features.Movies;

public class DeleteMovieRequest
{
    public int Id { get; set; }
}

public class DeleteMovieResponse
{
    public int Id { get; init; }
}

