namespace BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;

public class GetMovieResponse
{
    public int Id { get; init; }
    public required string Title { get; init; }
    public string? Director { get; init; }
    public int Rating { get; init; }
}
