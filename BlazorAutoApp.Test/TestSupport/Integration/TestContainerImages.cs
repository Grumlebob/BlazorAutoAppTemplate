using System.Globalization;
using Docker.DotNet.Models;

namespace BlazorAutoApp.Test.TestSupport.Integration;

internal static class TestContainerImages
{
    public const string PostgreSql = "postgres:18.4-alpine3.23";
    // PostgreSQL 18 declares /var/lib/postgresql as a Docker volume, so every
    // container would leave an anonymous volume behind on the shared runner.
    // Keep integration data on a bounded tmpfs instead. Testcontainers'
    // WithTmpfsMount accepts a destination only; options belong in HostConfig.Tmpfs.
    public const string PostgreSqlDataPath = "/var/lib/postgresql";
    public const string PostgreSqlDataTmpfsOptions = "rw,size=1073741824";
    public const string Redis = "redis:8.8.0-alpine3.23";
    public const string RedisDataPath = "/data";
    public const string RedisDataTmpfsOptions = "rw,size=67108864";
    public const string Ryuk = "testcontainers/ryuk:0.14.0";

    public static void ConfigurePostgreSqlData(CreateContainerParameters parameters) =>
        ConfigureDisposableData(parameters, PostgreSqlDataPath, PostgreSqlDataTmpfsOptions);

    public static void ConfigureRedisData(CreateContainerParameters parameters) =>
        ConfigureDisposableData(parameters, RedisDataPath, RedisDataTmpfsOptions);

    private static void ConfigureDisposableData(CreateContainerParameters parameters, string path, string options)
    {
        parameters.Volumes = new Dictionary<string, EmptyStruct>();
        parameters.HostConfig ??= new HostConfig();
        parameters.HostConfig.Binds = null!;
        parameters.HostConfig.Mounts = null!;
        parameters.HostConfig.Tmpfs = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            [path] = options
        };
    }
}

/// <summary>
/// Labels every container a test run creates, so cleanup on a self-hosted runner
/// shared by several repositories can prove which resources belong to which run.
/// </summary>
internal static class TestContainerLabels
{
    private static readonly string RunId = Environment.GetEnvironmentVariable("GITHUB_RUN_ID") is { Length: > 0 } runId
        ? runId
        : "local";

    private static readonly string RunAttempt = Environment.GetEnvironmentVariable("GITHUB_RUN_ATTEMPT") is { Length: > 0 } attempt
        ? attempt
        : "local";

    private static readonly string SessionId = RunId == "local"
        ? $"local-{Guid.NewGuid():N}"
        : $"{RunId}-{RunAttempt}";

    public static IReadOnlyDictionary<string, string> For(string purpose) =>
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["localcluster.ci.repository"] = Environment.GetEnvironmentVariable("GITHUB_REPOSITORY") is { Length: > 0 } repository
                ? repository
                : "local",
            ["localcluster.ci.owner"] = "tests",
            ["localcluster.ci.purpose"] = purpose,
            ["localcluster.ci.run_id"] = RunId,
            ["localcluster.ci.run_attempt"] = RunAttempt,
            ["localcluster.ci.session"] = SessionId,
            ["localcluster.ci.created_at"] = DateTimeOffset.UtcNow.ToString("O", CultureInfo.InvariantCulture)
        };
}
