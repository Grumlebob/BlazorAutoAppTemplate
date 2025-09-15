namespace BlazorAutoApp.Features.Inspections.Inspection;

public class InspectionEntityTypeConfiguration : IEntityTypeConfiguration<BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection>
{
    public void Configure(EntityTypeBuilder<BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection> entity)
    {
        entity.ToTable("Inspections");
        entity.HasKey(x => x.Id);
        entity.Property(x => x.Id).ValueGeneratedNever();
        entity.Property(x => x.CreatedAtUtc).IsRequired();

        entity.HasIndex(x => x.CompanyId);
        entity.HasOne<CompanyDetail>()
            .WithMany()
            .HasForeignKey(x => x.CompanyId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}

