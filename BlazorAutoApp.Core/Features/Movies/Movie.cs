using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Movies;

public class Movie
{
    [Key]
    public int Id { get; set; }

    [Required]
    [MaxLength(200)]
    public required string Title { get; set; }

    [MaxLength(200)]
    public string? Director { get; set; }

    [Range(0, 10)]
    public int Rating { get; set; }

    // Optional: allows adding without breaking existing data
    public int? ReleaseYear { get; set; }
}
