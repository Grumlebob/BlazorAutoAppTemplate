namespace BlazorAutoApp.Features.Inspections.VerifyInspectionEmail;

public class InspectionEntityTypeConfiguration : IEntityTypeConfiguration<BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection>
{
    public void Configure(EntityTypeBuilder<BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection> entity)
    {
        entity.ToTable("Inspections");
        entity.HasKey(x => x.Id);
        entity.Property(x => x.Id).ValueGeneratedNever();
        entity.Property(x => x.PasswordHash).IsRequired().HasMaxLength(512);
        entity.Property(x => x.PasswordSalt).IsRequired().HasMaxLength(512);
        entity.Property(x => x.CreatedAtUtc).IsRequired();
        entity.Property(x => x.VerifiedAtUtc).IsRequired(false);

        entity.HasIndex(x => x.CompanyId);
        entity.HasOne<CompanyDetail>()
            .WithMany()
            .HasForeignKey(x => x.CompanyId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
