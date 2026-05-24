using BlazorAutoApp.Core.Features.Movies.Domain;

namespace BlazorAutoApp.Features.Movies.Persistence;

public class MovieEntityTypeConfiguration : IEntityTypeConfiguration<Movie>
{
    public void Configure(EntityTypeBuilder<Movie> entity)
    {
        entity.HasKey(m => m.Id);
        entity.Property(m => m.Title).IsRequired().HasMaxLength(200);
        entity.Property(m => m.Director).HasMaxLength(200);
        entity.Property(m => m.Rating).IsRequired();
        // ReleaseYear is optional by default due to nullable int
    }
}
