using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;

public class CreateMovieRequest
{
    [Required]
    [StringLength(200)]
    public required string Title { get; set; }

    [StringLength(200)]
    public string? Director { get; set; }

    [Range(0, 10)]
    public int Rating { get; set; }
}
