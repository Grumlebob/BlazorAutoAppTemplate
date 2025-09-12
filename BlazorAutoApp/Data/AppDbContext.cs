
namespace BlazorAutoApp.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    public DbSet<Movie> Movies => Set<Movie>();
    public DbSet<HullImage> HullImages => Set<HullImage>();
    public DbSet<CompanyDetail> CompanyDetails => Set<CompanyDetail>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection> Inspections => Set<BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow> InspectionFlows => Set<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionVesselPart> InspectionVesselParts => Set<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionVesselPart>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Vessel> Vessels => Set<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Vessel>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Apply per-feature configurations
        modelBuilder.ApplyConfiguration(new Features.Movies.MovieEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.HullImages.HullImageEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.StartHullInspectionEmail.CompanyDetailEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VerifyInspectionEmail.InspectionEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.InspectionFlow.InspectionFlowEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.InspectionFlow.InspectionVesselPartEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.InspectionFlow.VesselEntityTypeConfiguration());
    }
}
