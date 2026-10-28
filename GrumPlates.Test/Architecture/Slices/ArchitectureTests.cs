using GrumPlates.Test.Architecture.Support;

namespace GrumPlates.Test.Architecture.Slices;

public class ArchitectureTests
{
    private const string CoreFeaturePrefix = "GrumPlates.Core.Features.";
    private const string ServerFeaturePrefix = "GrumPlates.Features.";
    private const string ClientFeaturePrefix = "GrumPlates.Client.Features.";

    [Fact]
    public void ForEachCoreApiInterface_HasServerAndClientImplementation()
    {
        var apiInterfaces = CoreApiInterfaces();

        Assert.NotEmpty(apiInterfaces);

        var failures = new List<string>();

        foreach (var api in apiInterfaces)
        {
            var serverCount = ArchitectureAssemblies.Server.GetTypes()
                .Count(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t));
            var clientCount = ArchitectureAssemblies.Client.GetTypes()
                .Count(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t));

            if (serverCount != 1 || clientCount != 1)
            {
                var root = SourceSearch.GetRepoRoot();
                var apiHint = string.Join("\n", SourceSearch.FindTypeHints(root, "GrumPlates.Core", api));
                var hintBlock = string.IsNullOrWhiteSpace(apiHint) ? string.Empty : $"\n  > {apiHint.Replace("\n", "\n  > ")}";
                failures.Add($"{api.FullName}: expected exactly 1 server and 1 client implementation, found server={serverCount}, client={clientCount}{hintBlock}");
            }
        }

        Assert.True(failures.Count == 0, "Implementation count violations:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void Implementations_LiveIn_FeatureNamespaces()
    {
        var apiInterfaces = CoreApiInterfaces();

        Assert.NotEmpty(apiInterfaces);

        var failures = new List<string>();

        foreach (var api in apiInterfaces)
        {
            var featurePath = GetFeaturePath(api);
            if (featurePath is null)
            {
                failures.Add($"{api.FullName}: API interfaces must live under {CoreFeaturePrefix}{{Feature}}.Contracts");
                continue;
            }

            var expectedServerPrefix = ServerFeaturePrefix + featurePath;
            var expectedClientPrefix = ClientFeaturePrefix + featurePath;

            var serverImpls = ArchitectureAssemblies.Server.GetTypes()
                .Where(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t))
                .ToList();

            var clientImpls = ArchitectureAssemblies.Client.GetTypes()
                .Where(t => t.IsClass && !t.IsAbstract && api.IsAssignableFrom(t))
                .ToList();

            if (serverImpls.Any(t => t.Namespace is null || !t.Namespace.StartsWith(expectedServerPrefix, StringComparison.Ordinal)))
            {
                var root = SourceSearch.GetRepoRoot();
                var hints = serverImpls.SelectMany(t => SourceSearch.FindTypeHints(root, "GrumPlates", t));
                failures.Add($"{api.FullName}: server implementations must live under {expectedServerPrefix}.* (found: {string.Join(", ", serverImpls.Select(x => x.FullName))})\n  > " + string.Join("\n  > ", hints));
            }

            if (clientImpls.Any(t => t.Namespace is null || !t.Namespace.StartsWith(expectedClientPrefix, StringComparison.Ordinal)))
            {
                var root = SourceSearch.GetRepoRoot();
                var hints = clientImpls.SelectMany(t => SourceSearch.FindTypeHints(root, "GrumPlates.Client", t));
                failures.Add($"{api.FullName}: client implementations must live under {expectedClientPrefix}.* (found: {string.Join(", ", clientImpls.Select(x => x.FullName))})\n  > " + string.Join("\n  > ", hints));
            }
        }

        Assert.True(failures.Count == 0, "Feature namespace violations:\n" + string.Join("\n", failures));
    }

    [Fact]
    public void ClientAssembly_HasNo_ServiceNamespace()
    {
        var offenders = ArchitectureAssemblies.Client.GetTypes()
            .Where(t => t.Namespace is not null && t.Namespace.StartsWith("GrumPlates.Client.Services", StringComparison.Ordinal))
            .Select(t => t.FullName)
            .OrderBy(x => x)
            .ToList();

        Assert.True(offenders.Count == 0, "Client service namespace is not allowed:\n" + string.Join("\n", offenders));
    }

    private static List<Type> CoreApiInterfaces()
    {
        return ArchitectureAssemblies.Core.GetTypes()
            .Where(t => t.IsInterface && t.IsPublic && t.Name.EndsWith("Api", StringComparison.Ordinal))
            .ToList();
    }

    private static string? GetFeaturePath(Type api)
    {
        if (api.Namespace is null || !api.Namespace.StartsWith(CoreFeaturePrefix, StringComparison.Ordinal))
        {
            return null;
        }

        var relative = api.Namespace[CoreFeaturePrefix.Length..];
        var parts = relative.Split('.');
        var contractsIndex = Array.IndexOf(parts, "Contracts");
        if (contractsIndex <= 0)
        {
            return null;
        }

        return string.Join('.', parts.Take(contractsIndex));
    }
}
