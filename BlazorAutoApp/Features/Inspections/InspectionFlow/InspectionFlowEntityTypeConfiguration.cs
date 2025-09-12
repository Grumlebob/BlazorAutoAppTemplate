using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

namespace BlazorAutoApp.Features.Inspections.InspectionFlow;

public class InspectionFlowEntityTypeConfiguration : IEntityTypeConfiguration<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow>
{
    public void Configure(EntityTypeBuilder<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow> entity)
    {
        entity.ToTable("InspectionFlows");
        entity.HasKey(x => x.Id);
        entity.Property(x => x.Id).ValueGeneratedNever();
        entity.Property(x => x.VesselName).HasMaxLength(200);
        entity.Property(x => x.InspectionType).IsRequired();

        entity.HasMany(x => x.VesselParts)
              .WithOne()
              .HasForeignKey(x => x.InspectionId)
              .OnDelete(DeleteBehavior.Cascade);
    }
}

public class InspectionVesselPartEntityTypeConfiguration : IEntityTypeConfiguration<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionVesselPart>
{
    public void Configure(EntityTypeBuilder<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionVesselPart> entity)
    {
        entity.ToTable("InspectionVesselParts");
        entity.HasKey(x => x.Id);
        entity.Property(x => x.PartCode).IsRequired().HasMaxLength(100);
        entity.Property(x => x.HullImageId).IsRequired(false);
        entity.HasIndex(x => new { x.InspectionId, x.PartCode });
    }
}

public class VesselEntityTypeConfiguration : IEntityTypeConfiguration<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Vessel>
{
    public void Configure(EntityTypeBuilder<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Vessel> entity)
    {
        entity.ToTable("Vessels");
        entity.HasKey(x => x.Id);
        entity.Property(x => x.Name).IsRequired().HasMaxLength(200);
        entity.HasIndex(x => x.Name).IsUnique();
    }
}
