using GrumPlates.Core.Features.Books.Domain;
using GrumPlates.Features.Login.Account;
using GrumPlates.Features.Books.Persistence;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.AspNetCore.DataProtection.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using GrumPlates.Features.Login.Accounts.Persistence;

namespace GrumPlates.Infrastructure.Persistence;

public class AppDbContext(DbContextOptions<AppDbContext> options)
    : IdentityDbContext<
        ApplicationUser,
        IdentityRole,
        string,
        IdentityUserClaim<string>,
        IdentityUserRole<string>,
        IdentityUserLogin<string>,
        IdentityRoleClaim<string>,
        IdentityUserToken<string>,
        IdentityUserPasskey<string>>(options), IDataProtectionKeyContext
{
    public DbSet<Book> Books => Set<Book>();
    public DbSet<UserBook> UserBooks => Set<UserBook>();
    public DbSet<AuthorBook> AuthorBooks => Set<AuthorBook>();
    public DbSet<DataProtectionKey> DataProtectionKeys => Set<DataProtectionKey>();
    internal DbSet<AccountOutboxMessage> AccountOutbox => Set<AccountOutboxMessage>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.ApplyConfiguration(new BookEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new UserBookEntityTypeConfiguration());
        modelBuilder.ApplyConfiguration(new AuthorBookEntityTypeConfiguration());

        modelBuilder.Entity<ApplicationUser>()
            .HasIndex(user => user.NormalizedEmail)
            .IsUnique()
            .HasDatabaseName("EmailIndex")
            .HasFilter("\"NormalizedEmail\" IS NOT NULL");

        modelBuilder.Entity<DataProtectionKey>().ToTable("DataProtectionKeys");

        modelBuilder.Entity<AccountOutboxMessage>(entity =>
        {
            entity.ToTable("AccountOutbox");
            entity.HasKey(message => message.Id);
            entity.Property(message => message.MessageId).HasMaxLength(254).IsRequired();
            entity.Property(message => message.UserId).HasMaxLength(450).IsRequired();
            entity.Property(message => message.Purpose).HasMaxLength(32).IsRequired();
            entity.Property(message => message.Status).HasMaxLength(16).IsRequired();
            entity.Property(message => message.ProtectedPayload).HasColumnType("text").IsRequired();
            entity.Property(message => message.LeaseId).HasMaxLength(36);
            entity.Property(message => message.FailureCode).HasMaxLength(64);
            entity.HasIndex(message => message.MessageId).IsUnique();
            entity.HasIndex(message => new { message.Status, message.NextAttemptUtc });
            entity.HasIndex(message => new { message.UserId, message.Purpose })
                .IsUnique()
                .HasFilter("\"Status\" IN ('Pending', 'Leased')");
            entity.HasOne<ApplicationUser>()
                .WithMany()
                .HasForeignKey(message => message.UserId)
                .OnDelete(DeleteBehavior.Cascade);
        });
    }
}
