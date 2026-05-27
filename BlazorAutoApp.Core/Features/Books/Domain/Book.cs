using System.ComponentModel.DataAnnotations;
using BlazorAutoApp.Core.Features.Books.Contracts;

namespace BlazorAutoApp.Core.Features.Books.Domain;

public class Book
{
    [Key]
    public int Id { get; set; }

    [Required]
    [MaxLength(BookRules.TitleMaxLength)]
    public required string Title { get; set; }

    [MaxLength(BookRules.AuthorMaxLength)]
    public string? Author { get; set; }

    [MaxLength(BookRules.UrlMaxLength)]
    public string? Url { get; set; }

    [Required]
    [MaxLength(BookRules.OwnerUserIdMaxLength)]
    public required string OwnerUserId { get; set; }
}
