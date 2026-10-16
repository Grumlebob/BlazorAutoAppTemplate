using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using BlazorAutoApp.Core.Features.Books.Domain;
using BlazorAutoApp.Core.Features.Login.UseCases.Shared;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Accounts.Email;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Accounts;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountDataManagementTests
{
    [Fact]
    public async Task Export_RequiresFreshPasswordAndReturnsOnlyTheUsersProfileAndOwnedBooks()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var owner = await fixture.CreateUserAsync();
        var other = await fixture.CreateUserAsync();
        int ownerPrivateId;
        int sharedCatalogId;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            ownerPrivateId = await AddBookAsync(db, "Owner private", owner.Id);
            _ = await AddBookAsync(db, "Other private", other.Id);
            sharedCatalogId = await AddBookAsync(db, "Public catalog", owner.Id, authorSeed: $"fixture-{Guid.NewGuid():N}");
        }

        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, owner.Email, owner.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);

        using (var rejected = await ExportAsync(client, owner.Id, session.CsrfToken, "incorrect current password"))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, rejected.StatusCode);
            Assert.Equal("CredentialsInvalid", await ReadCodeAsync(rejected));
        }

        using var response = await ExportAsync(client, owner.Id, session.CsrfToken, owner.Password);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var export = await response.Content.ReadFromJsonAsync<AccountExport>();
        Assert.NotNull(export);
        Assert.Equal(owner.Id, export.User.Id);
        Assert.Equal(owner.Email, export.User.Email);
        Assert.Equal(new[] { ownerPrivateId, sharedCatalogId }, export.Books.Select(book => book.Id).Order().ToArray());
        Assert.DoesNotContain(export.Books, book => book.Title == "Other private");
        var json = await response.Content.ReadAsStringAsync();
        Assert.DoesNotContain("SecurityStamp", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("PasswordHash", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("AccountOutbox", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("ProtectedPayload", json, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Export_Returns413InsteadOfTruncatingMoreThanTenThousandRecords()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var owner = await fixture.CreateUserAsync();
        await InsertOwnedBooksAsync(fixture, owner.Id, 10_001, urlLength: 0);
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, owner.Email, owner.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);

        using var response = await ExportAsync(client, owner.Id, session.CsrfToken, owner.Password);

        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, response.StatusCode);
        Assert.Equal("ExportTooLarge", await ReadCodeAsync(response));
    }

    [Fact]
    public async Task Export_Returns413WhenTheSerializedResultWouldExceedTenMiB()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var owner = await fixture.CreateUserAsync();
        await InsertOwnedBooksAsync(fixture, owner.Id, 5_500, urlLength: 2048);
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, owner.Email, owner.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);

        using var response = await ExportAsync(client, owner.Id, session.CsrfToken, owner.Password);

        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, response.StatusCode);
        Assert.Equal("ExportTooLarge", await ReadCodeAsync(response));
    }

    [Fact]
    public async Task Delete_RequiresCurrentPasswordAndPreservesOtherUsersAndSharedCatalogData()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var owner = await fixture.CreateUserAsync();
        var other = await fixture.CreateUserAsync();
        int privateBookId;
        int sharedBookId;
        int otherBookId;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            privateBookId = await AddBookAsync(db, "Private to delete", owner.Id);
            sharedBookId = await AddBookAsync(db, "Shared catalog to preserve", owner.Id, authorSeed: $"catalog-{Guid.NewGuid():N}");
            otherBookId = await AddBookAsync(db, "Other user's private book", other.Id);
        }
        await QueueResetIntentAsync(fixture, owner.Id, owner.Email);
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, owner.Email, owner.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);

        using (var rejected = await DeleteAsync(client, owner.Id, session.CsrfToken, "incorrect current password"))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, rejected.StatusCode);
            Assert.Equal("CredentialsInvalid", await ReadCodeAsync(rejected));
        }
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            Assert.NotNull(await db.Users.FindAsync(owner.Id));
            var intent = await db.AccountOutbox.SingleAsync(message => message.UserId == owner.Id);
            Assert.Equal("Pending", intent.Status);
            Assert.NotEmpty(intent.ProtectedPayload);
        }

        using var deleted = await DeleteAsync(client, owner.Id, session.CsrfToken, owner.Password);
        Assert.Equal(HttpStatusCode.OK, deleted.StatusCode);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            Assert.Null(await db.Users.FindAsync(owner.Id));
            Assert.False(await db.Books.AnyAsync(book => book.Id == privateBookId));
            Assert.True(await db.Books.AnyAsync(book => book.Id == sharedBookId));
            Assert.True(await db.AuthorBooks.AnyAsync(book => book.BookId == sharedBookId));
            Assert.False(await db.UserBooks.AnyAsync(book => book.OwnerUserId == owner.Id));
            Assert.True(await db.Books.AnyAsync(book => book.Id == otherBookId));
            Assert.True(await db.UserBooks.AnyAsync(book => book.BookId == otherBookId && book.OwnerUserId == other.Id));
            Assert.False(await db.AccountOutbox.AnyAsync(message => message.UserId == owner.Id));
            Assert.NotNull(await db.Users.FindAsync(other.Id));
        }
    }

    [Fact]
    public async Task Delete_RollsBackMailCancellationAndBookRemovalWhenIdentityDeleteFails()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var owner = await fixture.CreateUserAsync();
        int privateBookId;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            privateBookId = await AddBookAsync(db, "Rollback private", owner.Id);
            await db.Database.ExecuteSqlRawAsync("""
                CREATE FUNCTION "fixture_reject_identity_delete"() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'synthetic identity delete failure'; END; $$;
                """);
            await db.Database.ExecuteSqlRawAsync("""
                CREATE TRIGGER "fixture_reject_identity_delete" BEFORE DELETE ON "AspNetUsers"
                FOR EACH ROW EXECUTE FUNCTION "fixture_reject_identity_delete"();
                """);
        }
        await QueueResetIntentAsync(fixture, owner.Id, owner.Email);
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, owner.Email, owner.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);

        try
        {
            using var response = await DeleteAsync(client, owner.Id, session.CsrfToken, owner.Password);
            Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
            Assert.Equal("AccountServiceUnavailable", await ReadCodeAsync(response));
        }
        finally
        {
            using var scope = fixture.Factory.Services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            await db.Database.ExecuteSqlRawAsync("DROP TRIGGER IF EXISTS \"fixture_reject_identity_delete\" ON \"AspNetUsers\";");
            await db.Database.ExecuteSqlRawAsync("DROP FUNCTION IF EXISTS \"fixture_reject_identity_delete\"();");
        }

        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            Assert.NotNull(await db.Users.FindAsync(owner.Id));
            Assert.True(await db.Books.AnyAsync(book => book.Id == privateBookId));
            var intent = await db.AccountOutbox.SingleAsync(message => message.UserId == owner.Id);
            Assert.Equal("Pending", intent.Status);
            Assert.NotEmpty(intent.ProtectedPayload);
        }
    }

    [Fact]
    public async Task Delete_VerifiesLostCommitAcknowledgementWithoutRepeatingAccountDeletion()
    {
        var interceptor = new CommitUncertaintyInterceptor();
        await using var fixture = new RealCookieAccountFixture(
            configureTestServices: services => services.AddSingleton<IDbTransactionInterceptor>(interceptor));
        await fixture.InitializeAsync();
        var owner = await fixture.CreateUserAsync();
        int bookId;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            bookId = await AddBookAsync(scope.ServiceProvider.GetRequiredService<AppDbContext>(), "Commit recovery private book", owner.Id);
        }
        await QueueResetIntentAsync(fixture, owner.Id, owner.Email);
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, owner.Email, owner.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        interceptor.ThrowAfterNextCommit();

        using var deleted = await DeleteAsync(client, owner.Id, session.CsrfToken, owner.Password);

        Assert.Equal(HttpStatusCode.OK, deleted.StatusCode);
        Assert.Equal(1, interceptor.ThrownCount);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using var verification = fixture.Factory.Services.CreateScope();
        var db = verification.ServiceProvider.GetRequiredService<AppDbContext>();
        Assert.False(await db.Users.AnyAsync(user => user.Id == owner.Id));
        Assert.False(await db.Books.AnyAsync(book => book.Id == bookId));
        Assert.False(await db.AccountOutbox.AnyAsync(message => message.UserId == owner.Id));
    }

    private static async Task<int> AddBookAsync(AppDbContext db, string title, string ownerId, string? authorSeed = null)
    {
        var book = new Book { Title = title, Author = "Fixture author", Url = "https://example.test/book" };
        db.Books.Add(book);
        await db.SaveChangesAsync();
        db.UserBooks.Add(new UserBook { BookId = book.Id, OwnerUserId = ownerId });
        if (authorSeed is not null) db.AuthorBooks.Add(new AuthorBook { BookId = book.Id, SeedKey = authorSeed });
        await db.SaveChangesAsync();
        return book.Id;
    }

    private static async Task InsertOwnedBooksAsync(RealCookieAccountFixture fixture, string userId, int count, int urlLength)
    {
        using var scope = fixture.Factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        await db.Database.ExecuteSqlInterpolatedAsync($"""
            WITH inserted_books AS (
                INSERT INTO "Books" ("Title", "Author", "Url")
                SELECT 'Export bound ' || n::text, NULL, CASE WHEN {urlLength} = 0 THEN NULL ELSE repeat('x', {urlLength}) END
                FROM generate_series(1, {count}) AS n
                RETURNING "Id"
            )
            INSERT INTO "UserBooks" ("BookId", "OwnerUserId")
            SELECT "Id", {userId} FROM inserted_books
            """);
    }

    private static async Task QueueResetIntentAsync(RealCookieAccountFixture fixture, string userId, string email)
    {
        using var scope = fixture.Factory.Services.CreateScope();
        var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var user = await users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
        var token = await users.GeneratePasswordResetTokenAsync(user);
        var outbox = scope.ServiceProvider.GetRequiredService<AccountMailOutbox>();
        await outbox.RunAdmittedAsync(async (admission, cancellationToken) =>
        {
            var current = await admission.Users.FindByIdAsync(userId) ?? throw new InvalidOperationException("Fixture user missing.");
            await admission.Outbox.LockUserForUpdateAsync(current, cancellationToken);
            return await admission.Outbox.EnqueueAsync(current, AccountMailPurpose.PasswordReset, email, token,
                cancellationToken: cancellationToken);
        }, AccountMailEnqueueResult.Suppressed, CancellationToken.None);
    }

    private static Task<HttpResponseMessage> ExportAsync(HttpClient client, string userId, string csrfToken, string password) =>
        PostAccountAsync(client, "/api/auth/export", userId, csrfToken, new { password });

    private static Task<HttpResponseMessage> DeleteAsync(HttpClient client, string userId, string csrfToken, string password) =>
        PostAccountAsync(client, "/api/auth/delete", userId, csrfToken, new { password });

    private static async Task<HttpResponseMessage> PostAccountAsync(HttpClient client, string path, string userId, string csrfToken, object body)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, path) { Content = JsonContent.Create(body) };
        request.Headers.Add("X-Expected-User", userId);
        request.Headers.Add("X-CSRF-TOKEN", csrfToken);
        return await client.SendAsync(request);
    }

    private static async Task<string> ReadCodeAsync(HttpResponseMessage response)
    {
        using var json = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        return json.RootElement.GetProperty("code").GetString() ?? "";
    }
}
