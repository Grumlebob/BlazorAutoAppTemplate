using Npgsql;

namespace BlazorAutoApp.Infrastructure.Persistence;

internal sealed class DatabaseOptions
{
    public const string SectionName = "Database";

    public string? Host { get; init; }
    public int Port { get; init; } = 5432;
    public string? Name { get; init; }
    public string? Username { get; init; }
    public string? Password { get; init; }

    public bool HasRequiredValues()
    {
        return HasValue(Host) &&
            Port > 0 &&
            HasValue(Name) &&
            HasValue(Username) &&
            HasValue(Password);
    }

    public string ToConnectionString()
    {
        ValidateRequired(Host, nameof(Host));
        ValidateRequired(Name, nameof(Name));
        ValidateRequired(Username, nameof(Username));
        ValidateRequired(Password, nameof(Password));

        return new NpgsqlConnectionStringBuilder
        {
            Host = Host,
            Port = Port,
            Database = Name,
            Username = Username,
            Password = Password,
            GssEncryptionMode = GssEncryptionMode.Disable
        }.ConnectionString;
    }

    private static bool HasValue(string? value)
    {
        return !string.IsNullOrWhiteSpace(value) &&
            !string.Equals(value, "INJECT_THIS_IN_ORDER_TO_RUN", StringComparison.OrdinalIgnoreCase);
    }

    private static void ValidateRequired(string? value, string name)
    {
        if (!HasValue(value))
        {
            throw new InvalidOperationException($"Missing required Database:{name} configuration.");
        }
    }
}
