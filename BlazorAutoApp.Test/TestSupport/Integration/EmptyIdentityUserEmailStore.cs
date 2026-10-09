using BlazorAutoApp.Features.Login.Account;
using Microsoft.AspNetCore.Identity;

namespace BlazorAutoApp.Test.TestSupport.Integration;

/// <summary>Represents an empty Identity store for host tests that must not access a database.</summary>
internal sealed class EmptyIdentityUserEmailStore : IUserEmailStore<ApplicationUser>
{
    public Task<ApplicationUser?> FindByEmailAsync(string normalizedEmail, CancellationToken cancellationToken) =>
        Task.FromResult<ApplicationUser?>(null);

    public Task<string?> GetEmailAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<bool> GetEmailConfirmedAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<string?> GetNormalizedEmailAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task SetEmailAsync(ApplicationUser user, string? email, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task SetEmailConfirmedAsync(ApplicationUser user, bool confirmed, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task SetNormalizedEmailAsync(ApplicationUser user, string? normalizedEmail, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<ApplicationUser?> FindByIdAsync(string userId, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<ApplicationUser?> FindByNameAsync(string normalizedUserName, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<string> GetUserIdAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<string?> GetUserNameAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<string?> GetNormalizedUserNameAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task SetUserNameAsync(ApplicationUser user, string? userName, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task SetNormalizedUserNameAsync(ApplicationUser user, string? normalizedName, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<IdentityResult> CreateAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<IdentityResult> UpdateAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public Task<IdentityResult> DeleteAsync(ApplicationUser user, CancellationToken cancellationToken) =>
        throw new NotSupportedException();

    public void Dispose()
    {
    }
}
