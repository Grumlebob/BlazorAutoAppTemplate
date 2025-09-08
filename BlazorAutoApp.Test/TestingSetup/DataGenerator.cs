using BlazorAutoApp.Core.Features.Movies;
using Bogus;

namespace BlazorAutoApp.Test.TestingSetup;

public class DataGenerator //  test
{
    public readonly Faker<Movie> Generator = new Faker<Movie>(locale: "en");

    public DataGenerator()
    {
        // Let EF assign identity values; start as 0
        Generator.RuleFor(m => m.Id, _ => 0);
        Generator.RuleFor(m => m.Title, f => f.Lorem.Sentence(3, 2));
        Generator.RuleFor(m => m.Director, f => f.Name.FullName());
        Generator.RuleFor(m => m.Rating, f => f.Random.Int(0, 10));
        Generator.RuleFor(m => m.ReleaseYear, f => f.Random.Bool() ? f.Date.Past(40).Year : (int?)null);
    }
}
