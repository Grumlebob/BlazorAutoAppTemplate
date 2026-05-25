using System;
using System.Threading.Tasks;

namespace BlazorAutoApp.Test.TestSupport.Integration;

public static class Eventually
{
    public static async Task EventuallyAsync(
        Func<Task> assertion,
        TimeSpan? timeout = null,
        TimeSpan? pollInterval = null)
    {
        var stopAt = DateTimeOffset.UtcNow + (timeout ?? TimeSpan.FromSeconds(5));
        var interval = pollInterval ?? TimeSpan.FromMilliseconds(100);
        Exception? lastFailure = null;

        while (DateTimeOffset.UtcNow <= stopAt)
        {
            try
            {
                await assertion();
                return;
            }
            catch (Exception ex)
            {
                lastFailure = ex;
                await Task.Delay(interval);
            }
        }

        throw new TimeoutException("Condition was not met before the timeout elapsed.", lastFailure);
    }
}
