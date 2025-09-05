namespace BlazorAutoApp.Core.Features.Movies;

public class UpdateMovieRequest
{
    public int Id { get; set; }
    public required string Title { get; set; }
    public string? Director { get; set; }
    public int Rating { get; set; }
}

public class UpdateMovieResponse
{
    public int Id { get; init; }
    public required string Title { get; init; }
    public string? Director { get; init; }
    public int Rating { get; init; }
}

