using System.Security.Claims;
using System.Text.Encodings.Web;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.AspNetCore.Authentication;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace BlazorAutoApp.Test.TestSupport.Integration;

internal sealed class TestAuthenticationHandler(
    IOptionsMonitor<AuthenticationSchemeOptions> options,
    ILoggerFactory logger,
    UrlEncoder encoder,
    IDbContextFactory<AppDbContext> dbFactory)
    : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
{
    public const string SchemeName = "Test";
    public const string UserHeader = "X-Test-User";

    protected override async Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var userName = Request.Headers[UserHeader].FirstOrDefault();
        if (string.IsNullOrWhiteSpace(userName))
        {
            return AuthenticateResult.NoResult();
        }

        await EnsureUserExistsAsync(userName);
        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, userName),
            new Claim(ClaimTypes.Name, userName)
        };
        var identity = new ClaimsIdentity(claims, SchemeName);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, SchemeName);

        return AuthenticateResult.Success(ticket);
    }

    private async Task EnsureUserExistsAsync(string userName)
    {
        var normalized = userName.ToUpperInvariant();
        await using var db = await dbFactory.CreateDbContextAsync();
        if (await db.Users.AnyAsync(user => user.Id == userName))
        {
            return;
        }

        db.Users.Add(new ApplicationUser
        {
            Id = userName,
            UserName = userName,
            NormalizedUserName = normalized,
            Email = userName,
            NormalizedEmail = normalized,
            EmailConfirmed = true,
            SecurityStamp = Guid.NewGuid().ToString("N"),
            ConcurrencyStamp = Guid.NewGuid().ToString("N")
        });

        try
        {
            await db.SaveChangesAsync();
        }
        catch (DbUpdateException)
        {
            db.ChangeTracker.Clear();
        }
    }
}
