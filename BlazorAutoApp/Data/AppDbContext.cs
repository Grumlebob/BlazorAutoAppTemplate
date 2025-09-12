
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

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Apply per-feature configurations
        modelBuilder.ApplyConfiguration(new Features.Movies.MovieEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.HullImages.HullImageEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.StartHullInspectionEmail.CompanyDetailEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VerifyInspectionEmail.InspectionEntityTypeConfiguration());
    }
}
