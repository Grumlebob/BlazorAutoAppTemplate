using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Xunit;

namespace BlazorAutoApp.Test.Infrastructure.Hosting.CacheInvalidation;

public sealed class HybridCacheInvalidatorTests
{
    [Fact]
    public void CacheInvalidationResult_CopiesWarnings()
    {
        var warnings = new List<string> { "initial warning" };

        var result = new CacheInvalidationResult(
            localApplied: true,
            publishAttempted: true,
            published: false,
            warnings);

        warnings.Add("late mutation");

        Assert.Equal(["initial warning"], result.Warnings);
    }

    [Fact]
    public async Task InvalidateAsync_ReturnsWarning_WhenPublisherFailsAfterLocalApply()
    {
        var invalidator = new HybridCacheInvalidator(
            new RecordingApplier(),
            new ThrowingPublisher(new InvalidOperationException("publish failed")),
            Options.Create(new CacheInvalidationOptions
            {
                Enabled = true,
                AppName = "test-app",
                EnvironmentName = "Testing"
            }),
            NullLogger<HybridCacheInvalidator>.Instance);

        var result = await invalidator.InvalidateAsync(
            new CacheInvalidationRequest("test-scope", Keys: [], Tags: ["books"]));

        Assert.True(result.LocalApplied);
        Assert.True(result.PublishAttempted);
        Assert.False(result.Published);
        Assert.True(result.HasWarnings);
        Assert.Contains(result.Warnings, warning => warning.Contains("publish failed", StringComparison.Ordinal));
    }

    [Fact]
    public async Task InvalidateAsync_SkipsPublish_WhenInvalidationIsDisabled()
    {
        var invalidator = new HybridCacheInvalidator(
            new RecordingApplier(),
            new ThrowingPublisher(new InvalidOperationException("should not publish")),
            Options.Create(new CacheInvalidationOptions
            {
                Enabled = false,
                AppName = "test-app",
                EnvironmentName = "Testing"
            }),
            NullLogger<HybridCacheInvalidator>.Instance);

        var result = await invalidator.InvalidateAsync(
            new CacheInvalidationRequest("test-scope", Keys: [], Tags: ["books"]));

        Assert.True(result.LocalApplied);
        Assert.False(result.PublishAttempted);
        Assert.False(result.Published);
        Assert.Empty(result.Warnings);
    }

    [Fact]
    public async Task InvalidateAsync_PropagatesCallerCancellation()
    {
        using var cts = new CancellationTokenSource();
        await cts.CancelAsync();

        var invalidator = new HybridCacheInvalidator(
            new RecordingApplier(),
            new RecordingPublisher(),
            Options.Create(new CacheInvalidationOptions
            {
                Enabled = true,
                AppName = "test-app",
                EnvironmentName = "Testing"
            }),
            NullLogger<HybridCacheInvalidator>.Instance);

        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            invalidator.InvalidateAsync(
                new CacheInvalidationRequest("test-scope", Keys: [], Tags: ["books"]),
                cts.Token));
    }

    private sealed class RecordingApplier : ICacheInvalidationApplier
    {
        public Task ApplyAsync(CacheInvalidationRequest request, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return Task.CompletedTask;
        }
    }

    private sealed class RecordingPublisher : ICacheInvalidationPublisher
    {
        public Task PublishAsync(CacheInvalidationMessage message, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return Task.CompletedTask;
        }
    }

    private sealed class ThrowingPublisher(Exception exception) : ICacheInvalidationPublisher
    {
        public Task PublishAsync(CacheInvalidationMessage message, CancellationToken cancellationToken = default) =>
            Task.FromException(exception);
    }
}
