using BlazorAutoApp.Core.Features.Inspections.HullImages.Domain;
using InspectionFlowEntity = BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Domain.InspectionFlow;
using InspectionVesselPartEntity = BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Domain.InspectionVesselPart;

namespace BlazorAutoApp.Features.Inspections.InspectionFlow.Persistence;

public class InspectionFlowEntityTypeConfiguration : IEntityTypeConfiguration<InspectionFlowEntity>
{
    public void Configure(EntityTypeBuilder<InspectionFlowEntity> entity)
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

public class InspectionVesselPartEntityTypeConfiguration : IEntityTypeConfiguration<InspectionVesselPartEntity>
{
    public void Configure(EntityTypeBuilder<InspectionVesselPartEntity> entity)
    {
        entity.ToTable("InspectionVesselParts");
        entity.HasKey(x => x.Id);
        entity.Property(x => x.PartCode).IsRequired().HasMaxLength(100);
        entity.HasIndex(x => new { x.InspectionId, x.PartCode });
        // HullImages are linked from HullImages table via InspectionVesselPartId
    }
}

