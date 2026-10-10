namespace BlazorAutoApp.Features.Login;

internal interface ICurrentUserAccessor
{
    ValueTask<string?> GetCurrentUserIdAsync(CancellationToken cancellationToken = default);

    ValueTask<string> GetRequiredUserIdAsync(CancellationToken cancellationToken = default);
}
