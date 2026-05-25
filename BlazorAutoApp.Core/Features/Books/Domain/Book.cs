using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Books.Domain;

public class Book
{
    [Key]
    public int Id { get; set; }

    [Required]
    [MaxLength(200)]
    public required string Title { get; set; }

    [MaxLength(200)]
    public string? Author { get; set; }

    [MaxLength(2048)]
    public string? Url { get; set; }
}
