using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace BlazorAutoApp.Data;


public class AppDbContext : IdentityDbContext<ApplicationUser>
{
    private const string AdminRoleName = "Admin";
    private const string ViewerRoleName = "Viewer";

    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
    {
    }

    public DbSet<Movie> Movies => Set<Movie>();
    public DbSet<HullImage> HullImages => Set<HullImage>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection> Inspections => Set<BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow> InspectionFlows => Set<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionVesselPart> InspectionVesselParts => Set<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionVesselPart>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Vessel> Vessels => Set<BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Vessel>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.VesselPartDetails> VesselPartDetails => Set<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.VesselPartDetails>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.FoulingObservation> FoulingObservations => Set<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.FoulingObservation>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.CoatingCondition> CoatingConditions => Set<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.CoatingCondition>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.HullCondition> HullConditions => Set<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.HullCondition>();
    public DbSet<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.HullRating> HullRatings => Set<BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.HullRating>();

    public override int SaveChanges(bool acceptAllChangesOnSuccess)
    {
        ApplyDefaultIdentityRolesForNewUsers();
        return base.SaveChanges(acceptAllChangesOnSuccess);
    }

    public override Task<int> SaveChangesAsync(bool acceptAllChangesOnSuccess, CancellationToken cancellationToken = default)
    {
        ApplyDefaultIdentityRolesForNewUsers();
        return base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);
    }

    private void ApplyDefaultIdentityRolesForNewUsers()
    {
        var newUsers = ChangeTracker
            .Entries<ApplicationUser>()
            .Where(e => e.State == EntityState.Added)
            .Select(e => e.Entity)
            .ToList();

        if (newUsers.Count == 0)
        {
            return;
        }

        var viewerRoleId = Roles
            .AsNoTracking()
            .Where(r => r.Name == ViewerRoleName)
            .Select(r => r.Id)
            .FirstOrDefault();

        var adminRoleId = Roles
            .AsNoTracking()
            .Where(r => r.Name == AdminRoleName)
            .Select(r => r.Id)
            .FirstOrDefault();

        if (string.IsNullOrWhiteSpace(viewerRoleId) && string.IsNullOrWhiteSpace(adminRoleId))
        {
            return;
        }

        var hasPersistedUsers = Users.AsNoTracking().Any();
        var hasAdminUser = !string.IsNullOrWhiteSpace(adminRoleId) && UserRoles.AsNoTracking().Any(ur => ur.RoleId == adminRoleId);

        foreach (var user in newUsers)
        {
            if (string.IsNullOrWhiteSpace(user.Id))
            {
                continue;
            }

            if (!string.IsNullOrWhiteSpace(viewerRoleId))
            {
                UserRoles.Add(new IdentityUserRole<string>
                {
                    UserId = user.Id,
                    RoleId = viewerRoleId
                });
            }

            // Promote the first registered user to Admin automatically when no admin exists yet.
            if (!string.IsNullOrWhiteSpace(adminRoleId) && !hasPersistedUsers && !hasAdminUser)
            {
                UserRoles.Add(new IdentityUserRole<string>
                {
                    UserId = user.Id,
                    RoleId = adminRoleId
                });
                hasAdminUser = true;
            }

            hasPersistedUsers = true;
        }
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Apply per-feature configurations
        modelBuilder.ApplyConfiguration(new Features.Movies.MovieEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.HullImages.HullImageEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.Inspection.InspectionEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.InspectionFlow.InspectionFlowEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.InspectionFlow.InspectionVesselPartEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.InspectionFlow.VesselEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.VesselPartDetailsEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.FoulingObservationEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.CoatingConditionEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.HullConditionEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.HullRatingEntityTypeConfiguration());
    }
}
