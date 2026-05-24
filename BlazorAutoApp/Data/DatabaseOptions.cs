using Npgsql;

namespace BlazorAutoApp.Data;

internal sealed class DatabaseOptions
{
    public const string SectionName = "Database";

    public string? Host { get; init; }
    public int Port { get; init; } = 5432;
    public string? Name { get; init; }
    public string? Username { get; init; }
    public string? Password { get; init; }

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

    private static void ValidateRequired(string? value, string name)
    {
        if (string.IsNullOrWhiteSpace(value) ||
            string.Equals(value, "INJECT_THIS_IN_ORDER_TO_RUN", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"Missing required Database:{name} configuration.");
        }
    }
}
