namespace BlazorAutoApp.Features.HullImages;

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
        entity.ToTable("HullImages");
    }
}

