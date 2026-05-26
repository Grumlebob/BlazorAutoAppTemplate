using BlazorAutoApp.Core.Features.Books.Domain;
using BlazorAutoApp.Features.Login.Account;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace BlazorAutoApp.Features.Books.Persistence;

public class BookEntityTypeConfiguration : IEntityTypeConfiguration<Book>
{
    public void Configure(EntityTypeBuilder<Book> entity)
    {
        entity.HasKey(m => m.Id);
        entity.Property(m => m.Title).IsRequired().HasMaxLength(200);
        entity.Property(m => m.Author).HasMaxLength(200);
        entity.Property(m => m.Url).HasMaxLength(2048);
        entity.Property(m => m.OwnerUserId).IsRequired().HasMaxLength(450);
        entity.HasIndex(m => m.OwnerUserId);
        entity
            .HasOne<ApplicationUser>()
            .WithMany()
            .HasForeignKey(m => m.OwnerUserId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
