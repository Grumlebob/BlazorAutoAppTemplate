using System.ComponentModel.DataAnnotations;

namespace GrumPlates.Infrastructure.Hosting;

internal sealed class AppOptions
{
    public const string SectionName = "App";

    [Required]
    [MinLength(1)]
    public string Name { get; init; } = "GrumPlates";
}
