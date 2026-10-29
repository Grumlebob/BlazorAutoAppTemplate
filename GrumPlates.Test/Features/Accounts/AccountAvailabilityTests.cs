using System.Data.Common;
using GrumPlates.Features.Accounts.Email;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.Hosting;

namespace GrumPlates.Test.Features.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
public sealed class AccountAvailabilityTests
{
    [Theory]
    [InlineData("/api/auth/session")]
    [InlineData("/api/auth/login")]
    [InlineData("/api/auth/register")]
    [InlineData("/api/books")]
    public async Task DatabaseRetryExhaustion_ReturnsDeclaredSafe503WithoutLeakingProviderDetails(string path)
    {
        var interceptor = new UnavailableDatabaseInterceptor();
        await using var fixture = new RealCookieAccountFixture(new Dictionary<string, string?>
        {
            ["Accounts:RegistrationEnabled"] = "true",
            ["Accounts:Email:Host"] = "localhost",
            ["Accounts:Email:Port"] = "1",
            ["Accounts:Email:From"] = "accounts@example.test",
            ["Accounts:PublicOrigin"] = "https://books.example.test"
        }, services =>
        {
            services.AddSingleton<DbCommandInterceptor>(interceptor);
            foreach (var registration in services.Where(service => service.ServiceType == typeof(IHostedService)
                && service.ImplementationType == typeof(AccountMailOutboxWorker)).ToArray()) services.Remove(registration);
        });
        await fixture.InitializeAsync();
        var user = await fixture.CreateUserAsync();
        using var client = fixture.CreateClient();
        var authenticatedPath = path.EndsWith("/session", StringComparison.Ordinal) || path == "/api/books";
        if (authenticatedPath)
        {
            using var login = await RealCookieAccountFixture.LoginAsync(client, user.Email, user.Password);
            Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        }
        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        using var request = new HttpRequestMessage(authenticatedPath ? HttpMethod.Get : HttpMethod.Post, path);
        if (path == "/api/books") request.Headers.Add("X-Expected-User", user.Id);
        if (request.Method == HttpMethod.Post)
        {
            request.Headers.Add("X-CSRF-TOKEN", session.CsrfToken);
            request.Content = JsonContent.Create(new { email = user.Email, password = user.Password, rememberMe = false });
        }
        interceptor.Arm();

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.True(response.Headers.CacheControl?.NoStore);
        using var problem = System.Text.Json.JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        Assert.Equal("AccountServiceUnavailable", problem.RootElement.GetProperty("code").GetString());
        Assert.DoesNotContain(UnavailableDatabaseInterceptor.PrivateCanary, problem.RootElement.GetRawText(), StringComparison.Ordinal);
    }

    private sealed class UnavailableDatabaseInterceptor : DbCommandInterceptor
    {
        public const string PrivateCanary = "private-provider-details-must-not-escape";
        private int _armed;
        public void Arm() => Interlocked.Exchange(ref _armed, 1);

        public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
            DbCommand command, CommandEventData eventData, InterceptionResult<DbDataReader> result, CancellationToken cancellationToken = default)
        {
            ThrowIfArmed();
            return base.ReaderExecutingAsync(command, eventData, result, cancellationToken);
        }

        public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
            DbCommand command, CommandEventData eventData, InterceptionResult<int> result, CancellationToken cancellationToken = default)
        {
            ThrowIfArmed();
            return base.NonQueryExecutingAsync(command, eventData, result, cancellationToken);
        }

        private void ThrowIfArmed()
        {
            if (Interlocked.Exchange(ref _armed, 0) == 1) throw new RetryLimitExceededException(PrivateCanary, new TimeoutException(PrivateCanary));
        }
    }
}
