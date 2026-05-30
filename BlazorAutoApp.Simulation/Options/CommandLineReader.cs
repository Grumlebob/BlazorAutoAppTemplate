namespace BlazorAutoApp.Simulation.Options;

internal sealed class CommandLineReader
{
    private readonly Dictionary<string, string?> _values;

    private CommandLineReader(Dictionary<string, string?> values)
    {
        _values = values;
    }

    public static CommandLineReader Read(IReadOnlyList<string> args)
    {
        var values = new Dictionary<string, string?>(StringComparer.OrdinalIgnoreCase);
        for (var index = 0; index < args.Count; index++)
        {
            var arg = args[index];
            if (!arg.StartsWith("--", StringComparison.Ordinal))
            {
                continue;
            }

            var option = arg[2..];
            var equalsIndex = option.IndexOf('=');
            if (equalsIndex >= 0)
            {
                values[Normalize(option[..equalsIndex])] = option[(equalsIndex + 1)..];
                continue;
            }

            var key = Normalize(option);
            if (index + 1 < args.Count && !args[index + 1].StartsWith("-", StringComparison.Ordinal))
            {
                values[key] = args[++index];
            }
            else
            {
                values[key] = "true";
            }
        }

        return new CommandLineReader(values);
    }

    public string? Get(string name) =>
        _values.TryGetValue(Normalize(name), out var value) && !string.Equals(value, "true", StringComparison.OrdinalIgnoreCase)
            ? value
            : null;

    public bool Has(string name) =>
        _values.ContainsKey(Normalize(name));

    private static string Normalize(string value) =>
        value.Trim().Replace('_', '-').ToLowerInvariant();
}
