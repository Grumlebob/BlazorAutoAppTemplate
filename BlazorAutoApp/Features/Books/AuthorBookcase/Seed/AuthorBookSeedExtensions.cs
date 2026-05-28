namespace BlazorAutoApp.Features.Books.AuthorBookcase.Seed;

internal static class AuthorBookSeedExtensions
{
    private const string SeedAtStartupKey = "AuthorBooks:SeedAtStartup";

    public static async Task SeedAuthorBooksAsync(this WebApplication app)
    {
        if (!app.Configuration.GetValue(SeedAtStartupKey, true))
        {
            return;
        }

        using var scope = app.Services.CreateScope();
        var seeder = scope.ServiceProvider.GetRequiredService<IAuthorBookSeeder>();
        await seeder.SeedAsync();
    }
}
