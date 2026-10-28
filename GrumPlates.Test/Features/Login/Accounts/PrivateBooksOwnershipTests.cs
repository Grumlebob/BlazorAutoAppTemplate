using System.Net;
using System.Net.Http.Json;
using GrumPlates.Core.Features.Books.UseCases.CreateBook;
using GrumPlates.Features.Login.Account;
using GrumPlates.Features.Login.Accounts;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace GrumPlates.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class PrivateBooksOwnershipTests
{
    [Fact]
    public async Task RealCookieUsersAndAdmin_CanOnlyReadAndChangeTheirOwnBooks()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var adminEmail = $"admin-{Guid.NewGuid():N}@example.test";
        var adminPassword = NewPassword();
        await AdminAccountSeed.SeedConfiguredAdminAsync(new AccountOptions
        {
            Enabled = true,
            AdminSeed = new AdminSeedOptions { Enabled = true, Email = adminEmail, Password = adminPassword }
        }, fixture.Factory.Services, NullLogger.Instance);
        var alice = await fixture.CreateUserAsync();
        var bob = await fixture.CreateUserAsync();

        using var aliceClient = fixture.CreateClient();
        using var bobClient = fixture.CreateClient();
        using var adminClient = fixture.CreateClient();
        using var aliceLogin = await RealCookieAccountFixture.LoginAsync(aliceClient, alice.Email, alice.Password);
        using var bobLogin = await RealCookieAccountFixture.LoginAsync(bobClient, bob.Email, bob.Password);
        using var adminLogin = await RealCookieAccountFixture.LoginAsync(adminClient, adminEmail, adminPassword);
        Assert.Equal(HttpStatusCode.OK, aliceLogin.StatusCode);
        Assert.Equal(HttpStatusCode.OK, bobLogin.StatusCode);
        Assert.Equal(HttpStatusCode.OK, adminLogin.StatusCode);
        var aliceSession = await RealCookieAccountFixture.ReadSessionAsync(aliceClient);
        var bobSession = await RealCookieAccountFixture.ReadSessionAsync(bobClient);
        var adminSession = await RealCookieAccountFixture.ReadSessionAsync(adminClient);
        Assert.Contains("Admin", adminSession.User!.Roles);
        var aliceUserId = aliceSession.User!.Id;
        var bobUserId = bobSession.User!.Id;
        var adminUserId = adminSession.User!.Id;

        var aliceBook = await CreateBookAsync(aliceClient, aliceUserId, aliceSession.CsrfToken, "Alice private book");
        var bobBook = await CreateBookAsync(bobClient, bobUserId, bobSession.CsrfToken, "Bob private book");
        Assert.NotEqual(aliceBook.Id, bobBook.Id);
        Assert.Equal(new[] { "Alice private book" }, await ReadBookTitlesAsync(aliceClient, aliceUserId));
        Assert.Equal(new[] { "Bob private book" }, await ReadBookTitlesAsync(bobClient, bobUserId));
        Assert.Empty(await ReadBookTitlesAsync(adminClient, adminUserId));

        using (var hidden = await SendJsonAsync(bobClient, HttpMethod.Get, $"/api/books/{aliceBook.Id}", bobUserId, bobSession.CsrfToken))
        {
            Assert.Equal(HttpStatusCode.NotFound, hidden.StatusCode);
        }
        using (var updateOther = await SendJsonAsync(bobClient, HttpMethod.Put, $"/api/books/{aliceBook.Id}", bobUserId, bobSession.CsrfToken,
            new { id = aliceBook.Id, title = "Tampered", author = "Attacker", url = "https://attacker.example.test" }))
        {
            Assert.Equal(HttpStatusCode.NotFound, updateOther.StatusCode);
        }
        using (var deleteOther = await SendJsonAsync(bobClient, HttpMethod.Delete, $"/api/books/{aliceBook.Id}", bobUserId, bobSession.CsrfToken))
        {
            Assert.Equal(HttpStatusCode.NotFound, deleteOther.StatusCode);
        }

        using (var updateOwn = await SendJsonAsync(aliceClient, HttpMethod.Put, $"/api/books/{aliceBook.Id}", aliceUserId, aliceSession.CsrfToken,
            new { id = aliceBook.Id, title = "Alice updated book", author = "Alice", url = "https://alice.example.test" }))
        {
            Assert.Equal(HttpStatusCode.NoContent, updateOwn.StatusCode);
        }
        using (var deleteOwn = await SendJsonAsync(bobClient, HttpMethod.Delete, $"/api/books/{bobBook.Id}", bobUserId, bobSession.CsrfToken))
        {
            Assert.Equal(HttpStatusCode.NoContent, deleteOwn.StatusCode);
        }

        Assert.Equal(new[] { "Alice updated book" }, await ReadBookTitlesAsync(aliceClient, aliceUserId));
        Assert.Empty(await ReadBookTitlesAsync(bobClient, bobUserId));
        Assert.Empty(await ReadBookTitlesAsync(adminClient, adminUserId));
    }

    private static async Task<CreateBookResponse> CreateBookAsync(HttpClient client, string userId, string csrf, string title)
    {
        using var response = await SendJsonAsync(client, HttpMethod.Post, "/api/books", userId, csrf,
            new { title, author = "Fixture author", url = "https://example.test/book" });
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        return await response.Content.ReadFromJsonAsync<CreateBookResponse>()
            ?? throw new InvalidOperationException("Create-book fixture response was missing.");
    }

    private static async Task<string[]> ReadBookTitlesAsync(HttpClient client, string userId)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/books");
        request.Headers.Add("X-Expected-User", userId);
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var result = await response.Content.ReadFromJsonAsync<BookListResponse>();
        return result?.Books.Select(book => book.Title).ToArray() ?? [];
    }

    private static async Task<HttpResponseMessage> SendJsonAsync(
        HttpClient client,
        HttpMethod method,
        string path,
        string userId,
        string csrf,
        object? body = null)
    {
        using var request = new HttpRequestMessage(method, path);
        if (body is not null) request.Content = JsonContent.Create(body);
        request.Headers.Add("X-Expected-User", userId);
        request.Headers.Add("X-CSRF-TOKEN", csrf);
        return await client.SendAsync(request);
    }

    private static string NewPassword() => $"Seed admin phrase {Guid.NewGuid():N}";

    private sealed record BookListResponse(IReadOnlyList<BookListItem> Books);
    private sealed record BookListItem(int Id, string Title, string Author, string? Url);
}
