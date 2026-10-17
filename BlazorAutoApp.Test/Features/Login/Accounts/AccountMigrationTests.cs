using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace BlazorAutoApp.Test.Features.Login.Accounts;

public sealed class AccountMigrationTests
{
    private static readonly ServiceProvider IdentitySchemaVersionServices = new ServiceCollection()
        .Configure<IdentityOptions>(options => options.Stores.SchemaVersion = IdentitySchemaVersions.Version3)
        .BuildServiceProvider();

    [Fact]
    public async Task CleanUpgrade_CreatesUniqueEmailOutboxAndDataProtectionKeyStorage()
    {
        await using var container = await StartDatabaseAsync();
        await using var db = CreateDb(container);

        await db.Database.MigrateAsync();
        var indexDefinition = await ScalarAsync<string>(db,
            "SELECT indexdef FROM pg_indexes WHERE schemaname = current_schema() AND indexname = 'EmailIndex'");
        Assert.Contains("UNIQUE", indexDefinition, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("WHERE (\"NormalizedEmail\" IS NOT NULL)", indexDefinition, StringComparison.OrdinalIgnoreCase);

        Assert.True(await TableExistsAsync(db, "AccountOutbox"));
        Assert.True(await TableExistsAsync(db, "DataProtectionKeys"));
        Assert.True(await ColumnExistsAsync(db, "AccountOutbox", "ProtectedPayload"));
        Assert.False(await ColumnExistsAsync(db, "AccountOutbox", "Recipient"));
        Assert.False(await ColumnExistsAsync(db, "AccountOutbox", "Token"));
        Assert.False(await ColumnExistsAsync(db, "AccountOutbox", "Body"));
    }

    [Fact]
    public async Task DuplicateOrOversizedNormalizedEmails_RefuseUpgradeWithoutChangingAccounts()
    {
        await using var container = await StartDatabaseAsync();
        await using var db = CreateDb(container);
        var migrator = db.GetService<IMigrator>();
        await migrator.MigrateAsync("20260528104203_NormalizeBooksForAuthorBooks");
        await db.Database.ExecuteSqlRawAsync(
            """
            INSERT INTO "AspNetUsers"
                ("Id", "NormalizedEmail", "EmailConfirmed", "PhoneNumberConfirmed", "TwoFactorEnabled", "LockoutEnabled", "AccessFailedCount")
            VALUES
                ('migration-user-1', 'DUPLICATE@example.test', FALSE, FALSE, FALSE, FALSE, 0),
                ('migration-user-2', 'DUPLICATE@example.test', FALSE, FALSE, FALSE, FALSE, 0),
                ('migration-user-3', repeat('X', 255), FALSE, FALSE, FALSE, FALSE, 0);
            """);

        var failure = await Assert.ThrowsAsync<PostgresException>(() => migrator.MigrateAsync());
        Assert.Equal("23514", failure.SqlState);
        Assert.Contains("1 duplicate normalized-email groups", failure.MessageText, StringComparison.Ordinal);
        Assert.Contains("1 incompatible values", failure.MessageText, StringComparison.Ordinal);
        Assert.Contains("privately remediate", failure.MessageText, StringComparison.Ordinal);
        Assert.DoesNotContain("DUPLICATE@example.test", failure.MessageText, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(3L, await ScalarAsync<long>(db, "SELECT COUNT(*) FROM \"AspNetUsers\""));
        Assert.False(await TableExistsAsync(db, "AccountOutbox"));
    }

    private static async Task<PostgreSqlContainer> StartDatabaseAsync()
    {
        var container = TestContainerImages.CreatePostgreSqlFixture()
            .WithLabel(TestContainerLabels.For("account-migration-tests"))
            .WithCleanUp(true)
            .Build();
        await container.StartAsync();
        return container;
    }

    private static AppDbContext CreateDb(PostgreSqlContainer container) =>
        new(new DbContextOptionsBuilder<AppDbContext>()
            .UseApplicationServiceProvider(IdentitySchemaVersionServices)
            .UseNpgsql(container.GetConnectionString())
            .Options);

    private static async Task<bool> TableExistsAsync(AppDbContext db, string table) =>
        await ScalarAsync<bool>(db,
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = @table)",
            ("table", table));

    private static async Task<bool> ColumnExistsAsync(AppDbContext db, string table, string column) =>
        await ScalarAsync<bool>(db,
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = @table AND column_name = @column)",
            ("table", table), ("column", column));

    private static async Task<T> ScalarAsync<T>(AppDbContext db, string sql, params (string Name, object Value)[] parameters)
    {
        await db.Database.OpenConnectionAsync();
        await using var command = db.Database.GetDbConnection().CreateCommand();
        command.CommandText = sql;
        foreach (var (name, value) in parameters)
        {
            var parameter = command.CreateParameter();
            parameter.ParameterName = name;
            parameter.Value = value;
            command.Parameters.Add(parameter);
        }
        return (T)(await command.ExecuteScalarAsync())!;
    }
}
