using BlazorAutoApp.Core.Features.StartHullInspectionEmail;

namespace BlazorAutoApp.Features.StartHullInspectionEmail;

public class CompanyDetailEntityTypeConfiguration : IEntityTypeConfiguration<CompanyDetail>
{
    public void Configure(EntityTypeBuilder<CompanyDetail> entity)
    {
        entity.ToTable("CompanyDetails");
        entity.HasKey(x => x.Id);
        entity.Property(x => x.Name).IsRequired().HasMaxLength(200);
        entity.Property(x => x.Email).IsRequired().HasMaxLength(320);
        entity.Property(x => x.HasActivatedLatestInspectionEmail).HasDefaultValue(false);
    }
}
