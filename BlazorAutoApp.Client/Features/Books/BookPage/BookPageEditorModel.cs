using System.ComponentModel.DataAnnotations;
using BlazorAutoApp.Core.Features.Books.UseCases.Shared;

namespace BlazorAutoApp.Client.Features.Books.BookPage;

public sealed class BookPageEditorModel : IValidatableObject
{
    [Required]
    [StringLength(200)]
    public string Title { get; set; } = string.Empty;

    [StringLength(200)]
    public string? Author { get; set; }

    [StringLength(2048)]
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
