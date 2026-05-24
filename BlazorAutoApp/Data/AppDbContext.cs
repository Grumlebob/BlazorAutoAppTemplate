using BlazorAutoApp.Core.Features.Movies.Domain;
using BlazorAutoApp.Core.Features.Inspections.HullImages.Domain;
using BlazorAutoApp.Core.Features.Inspections.Inspection.Domain;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Domain;
using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Domain;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace BlazorAutoApp.Data;


public class AppDbContext(DbContextOptions<AppDbContext> options) : IdentityDbContext<ApplicationUser>(options)
{
    private const string AdminRoleName = "Admin";
    private const string ViewerRoleName = "Viewer";

    public DbSet<Movie> Movies => Set<Movie>();
    public DbSet<HullImage> HullImages => Set<HullImage>();
    public DbSet<Inspection> Inspections => Set<Inspection>();
    public DbSet<InspectionFlow> InspectionFlows => Set<InspectionFlow>();
    public DbSet<InspectionVesselPart> InspectionVesselParts => Set<InspectionVesselPart>();
    public DbSet<VesselPartDetails> VesselPartDetails => Set<VesselPartDetails>();
    public DbSet<FoulingObservation> FoulingObservations => Set<FoulingObservation>();
    public DbSet<CoatingCondition> CoatingConditions => Set<CoatingCondition>();
    public DbSet<HullCondition> HullConditions => Set<HullCondition>();
    public DbSet<HullRating> HullRatings => Set<HullRating>();

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
        modelBuilder.ApplyConfiguration(new Features.Movies.Persistence.MovieEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.HullImages.Persistence.HullImageEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.Inspection.Persistence.InspectionEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.InspectionFlow.Persistence.InspectionFlowEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.InspectionFlow.Persistence.InspectionVesselPartEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.Persistence.VesselPartDetailsEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.Persistence.FoulingObservationEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.Persistence.CoatingConditionEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.Persistence.HullConditionEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new Features.Inspections.VesselPartDetails.Persistence.HullRatingEntityTypeConfiguration());
    }
}
