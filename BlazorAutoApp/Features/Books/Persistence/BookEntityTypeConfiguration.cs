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
    }
}

public class UserBookEntityTypeConfiguration : IEntityTypeConfiguration<UserBook>
{
    public void Configure(EntityTypeBuilder<UserBook> entity)
    {
        entity.HasKey(m => m.BookId);
        entity.Property(m => m.OwnerUserId).IsRequired().HasMaxLength(BookRules.OwnerUserIdMaxLength);
        entity.HasIndex(m => m.OwnerUserId);
        entity
            .HasOne(m => m.Book)
            .WithOne()
            .HasForeignKey<UserBook>(m => m.BookId)
            .OnDelete(DeleteBehavior.Cascade);
        entity
            .HasOne<ApplicationUser>()
            .WithMany()
            .HasForeignKey(m => m.OwnerUserId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}

public class AuthorBookEntityTypeConfiguration : IEntityTypeConfiguration<AuthorBook>
{
    public void Configure(EntityTypeBuilder<AuthorBook> entity)
    {
        entity.HasKey(m => m.BookId);
        entity.Property(m => m.SeedKey).IsRequired().HasMaxLength(BookRules.AuthorSeedKeyMaxLength);
        entity.HasIndex(m => m.SeedKey).IsUnique();
        entity
            .HasOne(m => m.Book)
            .WithOne()
            .HasForeignKey<AuthorBook>(m => m.BookId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
