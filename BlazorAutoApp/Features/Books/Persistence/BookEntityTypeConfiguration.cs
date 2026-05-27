using BlazorAutoApp.Core.Features.Books.Contracts;
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
        entity.Property(m => m.Id).ValueGeneratedOnAdd();
        entity.Property(m => m.Title).IsRequired().HasMaxLength(BookRules.TitleMaxLength);
        entity.Property(m => m.Author).HasMaxLength(BookRules.AuthorMaxLength);
        entity.Property(m => m.Url).HasMaxLength(BookRules.UrlMaxLength);
        entity.Property(m => m.OwnerUserId).IsRequired().HasMaxLength(BookRules.OwnerUserIdMaxLength);
        entity.HasIndex(m => m.OwnerUserId);
        entity
            .HasOne<ApplicationUser>()
            .WithMany()
            .HasForeignKey(m => m.OwnerUserId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
