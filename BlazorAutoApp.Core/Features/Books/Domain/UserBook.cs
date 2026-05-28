using System.ComponentModel.DataAnnotations;
using BlazorAutoApp.Core.Features.Books.Contracts;

namespace BlazorAutoApp.Core.Features.Books.Domain;

public class UserBook
{
    [Key]
    public int BookId { get; set; }

    [Required]
    [MaxLength(BookRules.OwnerUserIdMaxLength)]
    public required string OwnerUserId { get; set; }

    public Book Book { get; set; } = null!;
}
