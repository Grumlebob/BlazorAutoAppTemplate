using System.Diagnostics;
using System.Text.Json;
using DotNet.Testcontainers.Builders;
using Testcontainers.PostgreSql;
using Xunit;

namespace BlazorAutoApp.Test.TestSupport.Integration;

public sealed class TestContainerLifecycleTests
{
    [Fact]
    public async Task DisposeAsync_RemovesTheOwnedContainer()
    {
        if (!string.Equals(Environment.GetEnvironmentVariable("RUN_TESTCONTAINER_LIFECYCLE"), "1", StringComparison.Ordinal))
        {
            Assert.Skip("Set RUN_TESTCONTAINER_LIFECYCLE=1 to run the isolated Docker lifecycle proof.");
        }

        var container = new ContainerBuilder("alpine:3.21")
            .WithCommand("sleep", "5")
            .WithLabel(TestContainerLabels.For("lifecycle-proof"))
            .WithCleanUp(true)
            .Build();
        var containerId = string.Empty;

        try
        {
            await container.StartAsync();
            containerId = container.Id;
            Assert.False(string.IsNullOrWhiteSpace(containerId));
            Assert.True(await DockerInspectSucceedsAsync(containerId));
        }
        finally
        {
            await container.DisposeAsync();
        }

        Assert.False(await DockerInspectSucceedsAsync(containerId));
    }

    [Fact]
    public async Task PostgreSqlFixture_UsesTmpfsInsteadOfAnAnonymousVolume()
    {
        if (!string.Equals(Environment.GetEnvironmentVariable("RUN_TESTCONTAINER_LIFECYCLE"), "1", StringComparison.Ordinal))
        {
            Assert.Skip("Set RUN_TESTCONTAINER_LIFECYCLE=1 to run the isolated Docker lifecycle proof.");
        }

        await using var container = new PostgreSqlBuilder(TestContainerImages.PostgreSql)
            .WithCreateParameterModifier(TestContainerImages.ConfigurePostgreSqlData)
            .WithLabel(TestContainerLabels.For("lifecycle-proof-postgres"))
            .WithCleanUp(true)
            .Build();

        await container.StartAsync();
        var inspect = await DockerInspectAsync(container.Id);
        var tmpfs = inspect.GetProperty("HostConfig").GetProperty("Tmpfs");
        Assert.Equal(
            TestContainerImages.PostgreSqlDataTmpfsOptions,
            tmpfs.GetProperty(TestContainerImages.PostgreSqlDataPath).GetString());
        var mounts = inspect.GetProperty("Mounts").EnumerateArray();
        Assert.DoesNotContain(mounts, mount =>
            string.Equals(mount.GetProperty("Type").GetString(), "volume", StringComparison.Ordinal)
            && string.Equals(mount.GetProperty("Destination").GetString(), TestContainerImages.PostgreSqlDataPath, StringComparison.Ordinal));
    }

    [Fact]
    public async Task RedisFixture_UsesBoundedTmpfsInsteadOfAnAnonymousVolume()
    {
        if (!string.Equals(Environment.GetEnvironmentVariable("RUN_TESTCONTAINER_LIFECYCLE"), "1", StringComparison.Ordinal))
        {
            Assert.Skip("Set RUN_TESTCONTAINER_LIFECYCLE=1 to run the isolated Docker lifecycle proof.");
        }

        await using var container = new ContainerBuilder(TestContainerImages.Redis)
            .WithCreateParameterModifier(TestContainerImages.ConfigureRedisData)
            .WithCommand("redis-server", "--save", "", "--appendonly", "no")
            .WithWaitStrategy(Wait.ForUnixContainer().UntilCommandIsCompleted("redis-cli", "ping"))
            .WithLabel(TestContainerLabels.For("lifecycle-proof-redis"))
            .WithCleanUp(true)
            .Build();

        await container.StartAsync();
        var inspect = await DockerInspectAsync(container.Id);
        Assert.Equal(
            TestContainerImages.RedisDataTmpfsOptions,
            inspect.GetProperty("HostConfig").GetProperty("Tmpfs").GetProperty(TestContainerImages.RedisDataPath).GetString());
        Assert.DoesNotContain(inspect.GetProperty("Mounts").EnumerateArray(), mount =>
            string.Equals(mount.GetProperty("Type").GetString(), "volume", StringComparison.Ordinal));
    }

    private static async Task<bool> DockerInspectSucceedsAsync(string containerId)
    {
        using var process = Process.Start(new ProcessStartInfo
        {
            FileName = "docker",
            ArgumentList = { "inspect", "--format", "{{.Id}}", containerId },
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        });

        if (process is null)
        {
            return false;
        }

        await process.WaitForExitAsync();
        return process.ExitCode == 0;
    }

    private static async Task<JsonElement> DockerInspectAsync(string containerId)
    {
        using var process = Process.Start(new ProcessStartInfo
        {
            FileName = "docker",
            ArgumentList = { "inspect", "--format", "{{json .}}", containerId },
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        });

        if (process is null)
        {
            return default;
        }

        var output = await process.StandardOutput.ReadToEndAsync();
        await process.WaitForExitAsync();
        if (process.ExitCode != 0)
        {
            return default;
        }

        using var document = JsonDocument.Parse(output);
        return document.RootElement.Clone();
    }
}
