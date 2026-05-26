using BlazorAutoApp.Core.Features.Books.Domain;
using Bogus;

namespace BlazorAutoApp.Test.Features.Books.TestData;

public class BookDataGenerator
{
    public const string DefaultOwnerUserId = BookTestUsers.DefaultUserId;

    public readonly Faker<Book> Generator = new(locale: "en");

    public BookDataGenerator()
    {
        // Let EF assign identity values; start as 0
        Generator.RuleFor(m => m.Id, _ => 0);
        Generator.RuleFor(m => m.Title, f => f.Lorem.Sentence(3, 2));
        Generator.RuleFor(m => m.Author, f => f.Name.FullName());
        Generator.RuleFor(m => m.Url, f => f.Internet.UrlWithPath("https"));
        Generator.RuleFor(m => m.OwnerUserId, _ => DefaultOwnerUserId);
    }
}
