using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.HullImages;

public class CreateHullImageRequest
{
    [Required]
    [MaxLength(512)]
    public required string OriginalFileName { get; set; }

    [MaxLength(200)]
    public string? ContentType { get; set; }

    public long ByteSize { get; set; }

    public string? Sha256 { get; set; }

    public int? Width { get; set; }
    public int? Height { get; set; }

    [Required]
    [MaxLength(512)]
    public required string StorageKey { get; set; }
}

public class CreateHullImageResponse
{
    public int Id { get; init; }
    public required string OriginalFileName { get; init; }
    public string? ContentType { get; init; }
    public long ByteSize { get; init; }
    public string? Sha256 { get; init; }
    public int? Width { get; init; }
    public int? Height { get; init; }
}
