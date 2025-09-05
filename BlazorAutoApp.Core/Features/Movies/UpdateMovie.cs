using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Movies;

public class UpdateMovieRequest
{
    public int Id { get; set; }

    [Required]
    [StringLength(200)]
    public required string Title { get; set; }

    [StringLength(200)]
    public string? Director { get; set; }

    [Range(0, 10)]
    public int Rating { get; set; }
}

public class UpdateMovieResponse
{
    public int Id { get; init; }
    public required string Title { get; init; }
    public string? Director { get; init; }
    public int Rating { get; init; }
}
