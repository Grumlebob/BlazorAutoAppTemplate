using BlazorAutoApp.Core.Features.Movies.Domain;
using Bogus;

namespace BlazorAutoApp.Test.Features.Movies.TestData;

public class MovieDataGenerator
{
    public readonly Faker<Movie> Generator = new(locale: "en");

    public MovieDataGenerator()
    {
        // Let EF assign identity values; start as 0
        Generator.RuleFor(m => m.Id, _ => 0);
        Generator.RuleFor(m => m.Title, f => f.Lorem.Sentence(3, 2));
        Generator.RuleFor(m => m.Director, f => f.Name.FullName());
        Generator.RuleFor(m => m.Rating, f => f.Random.Int(0, 10));
    }
}
