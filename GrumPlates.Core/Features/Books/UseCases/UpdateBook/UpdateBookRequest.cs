using System.ComponentModel.DataAnnotations;
using GrumPlates.Core.Features.Books.Contracts;
using GrumPlates.Core.Features.Books.UseCases.Shared;

namespace GrumPlates.Core.Features.Books.UseCases.UpdateBook;

public class UpdateBookRequest : IValidatableObject
{
    public int Id { get; set; }

    [Required]
    [StringLength(BookRules.TitleMaxLength)]
    public required string Title { get; set; }

    [StringLength(BookRules.AuthorMaxLength)]
    public string? Author { get; set; }

    [StringLength(BookRules.UrlMaxLength)]
    public string? Url { get; set; }

    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        if (!BookUrlValidation.IsValidOptionalHttpUrl(Url))
        {
            yield return new ValidationResult(
                "URL must be an absolute HTTP or HTTPS URL.",
                [nameof(Url)]);
        }
    }
}
