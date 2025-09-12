using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.HullImages;

public class HullImage
{
    [Key]
    public int Id { get; set; }

    [Required]
    [MaxLength(512)]
    public required string OriginalFileName { get; set; }

    [MaxLength(200)]
    public string? ContentType { get; set; }

    public long ByteSize { get; set; }

    [MaxLength(128)]
    public string? Sha256 { get; set; }

    public int? Width { get; set; }
    public int? Height { get; set; }

    [Required]
    [MaxLength(512)]
    public required string StorageKey { get; set; }

    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;

    [MaxLength(50)]
    public string Status { get; set; } = "Ready";

    public string? Notes { get; set; }

    // New fields
    public double AiHullScore { get; set; } = 0.0;

    [MaxLength(128)]
    public string VesselName { get; set; } = "BoatyBoat";

    // Link to Inspection Vessel Part (nullable; set when uploaded from Flow UI)
    public int? InspectionVesselPartId { get; set; }
}

