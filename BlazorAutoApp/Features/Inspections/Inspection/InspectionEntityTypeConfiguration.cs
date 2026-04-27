using InspectionEntity = BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection;

namespace BlazorAutoApp.Features.Inspections.Inspection;

public class InspectionEntityTypeConfiguration : IEntityTypeConfiguration<InspectionEntity>
{
    public void Configure(EntityTypeBuilder<InspectionEntity> entity)
    {
        entity.ToTable("Inspections");
        entity.HasKey(x => x.Id);
        entity.Property(x => x.Id).ValueGeneratedNever();
        entity.Property(x => x.CreatedAtUtc).IsRequired();
    }
}
