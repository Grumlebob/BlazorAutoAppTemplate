using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

namespace BlazorAutoApp.Features.Inspections.HullImages;

public class HullImageEntityTypeConfiguration : IEntityTypeConfiguration<HullImage>
{
    public void Configure(EntityTypeBuilder<HullImage> entity)
    {
        entity.HasKey(x => x.Id);
        entity.Property(x => x.OriginalFileName).IsRequired().HasMaxLength(512);
        entity.Property(x => x.ContentType).HasMaxLength(200);
        entity.Property(x => x.StorageKey).IsRequired().HasMaxLength(512);
        entity.Property(x => x.Sha256).HasMaxLength(128);
        entity.Property(x => x.Status).HasMaxLength(50);
        entity.Property(x => x.VesselName).IsRequired().HasMaxLength(128).HasDefaultValue("BoatyBoat");
        entity.Property(x => x.AiHullScore).HasDefaultValue(0.0);
        entity.ToTable("HullImages");

        // Optional link to a specific inspection vessel part
        entity.HasOne<InspectionVesselPart>()
              .WithMany(vp => vp.HullImages)
              .HasForeignKey(x => x.InspectionVesselPartId)
              .OnDelete(DeleteBehavior.SetNull);

        entity.HasIndex(x => x.InspectionVesselPartId);
    }
}

