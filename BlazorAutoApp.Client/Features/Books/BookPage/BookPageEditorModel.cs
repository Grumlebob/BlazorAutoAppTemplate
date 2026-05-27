using System.ComponentModel.DataAnnotations;
using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.UseCases.Shared;

namespace BlazorAutoApp.Client.Features.Books.BookPage;

public sealed class BookPageEditorModel : IValidatableObject
{
    [Required]
    [StringLength(BookRules.TitleMaxLength)]
    public string Title { get; set; } = string.Empty;

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
