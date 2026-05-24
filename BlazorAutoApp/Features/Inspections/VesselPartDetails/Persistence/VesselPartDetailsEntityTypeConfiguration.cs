using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;
using VesselPartDetailsEntity = BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain.VesselPartDetails;

namespace BlazorAutoApp.Features.Inspections.VesselPartDetails.Persistence;

public class VesselPartDetailsEntityTypeConfiguration : IEntityTypeConfiguration<VesselPartDetailsEntity>
{
    public void Configure(EntityTypeBuilder<VesselPartDetailsEntity> b)
    {
        b.ToTable("VesselPartDetails");
        b.HasKey(x => x.Id);
        b.HasIndex(x => x.InspectionVesselPartId).IsUnique();
        b.Property(x => x.Notes).HasMaxLength(4000).IsRequired(false);
    }
}

public class FoulingObservationEntityTypeConfiguration : IEntityTypeConfiguration<FoulingObservation>
{
    public void Configure(EntityTypeBuilder<FoulingObservation> b)
    {
        b.ToTable("FoulingObservations");
        b.HasKey(x => x.Id);
        b.Property(x => x.CoveragePercent);
    }
}

public class CoatingConditionEntityTypeConfiguration : IEntityTypeConfiguration<CoatingCondition>
{
    public void Configure(EntityTypeBuilder<CoatingCondition> b)
    {
        b.ToTable("CoatingConditions");
        b.HasKey(x => x.Id);
        b.Property(x => x.IntactPercent);
    }
}

public class HullConditionEntityTypeConfiguration : IEntityTypeConfiguration<HullCondition>
{
    public void Configure(EntityTypeBuilder<HullCondition> b)
    {
        b.ToTable("HullConditions");
        b.HasKey(x => x.Id);
        b.Property(x => x.IntegrityPercent);
    }
}

public class HullRatingEntityTypeConfiguration : IEntityTypeConfiguration<HullRating>
{
    public void Configure(EntityTypeBuilder<HullRating> b)
    {
        b.ToTable("HullRatings");
        b.HasKey(x => x.Id);
    }
}
