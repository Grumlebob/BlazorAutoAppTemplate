using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.CreateHullImage;

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

    [MaxLength(128)]
    public string? VesselName { get; set; } = "BoatyBoat";

    public int? InspectionVesselPartId { get; set; }
}
