namespace BlazorAutoApp.Core.Features.Movies;

public class GetMovieRequest
{
    public int Id { get; set; }
}

public class GetMovieResponse
{
    public int Id { get; init; }
    public required string Title { get; init; }
    public string? Director { get; init; }
    public int Rating { get; init; }
}

