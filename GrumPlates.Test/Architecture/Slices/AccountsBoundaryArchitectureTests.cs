using GrumPlates.Test.Architecture.Support;

namespace GrumPlates.Test.Architecture.Slices;

public class AccountsBoundaryArchitectureTests
{
    [Fact]
    public void ProductionAssemblies_RetainOnlyTheMappedUserInLegacyLoginNamespaces()
    {
        var legacyPrefixes = new[]
        {
            "GrumPlates.Core.Features.Login",
            "GrumPlates.Features.Login",
            "GrumPlates.Client.Features.Login"
        };
        var mappedUser = typeof(GrumPlates.Features.Login.Account.ApplicationUser);
        var legacyTypes = new[]
        {
            ArchitectureAssemblies.Core,
            ArchitectureAssemblies.Server,
            ArchitectureAssemblies.Client
        }.SelectMany(assembly => assembly.GetTypes())
            .Where(type => type.Namespace is { } typeNamespace && legacyPrefixes.Any(prefix =>
                typeNamespace == prefix || typeNamespace.StartsWith(prefix + ".", StringComparison.Ordinal)))
            .ToArray();

        Assert.Equal("GrumPlates.Features.Login.Account.ApplicationUser", mappedUser.FullName);
        Assert.Equal(new[] { mappedUser }, legacyTypes);
    }

    [Fact]
    public void ProductionSource_DoesNotUseTheRetiredLoginFeatureFolder()
    {
        var root = SourceSearch.GetRepoRoot();
        var projectFolders = new[] { "GrumPlates.Core", "GrumPlates", "GrumPlates.Client" };
        var offenders = projectFolders
            .Select(project => Path.Combine(root, project, "Features", "Login"))
            .Where(Directory.Exists)
            .SelectMany(folder => Directory.EnumerateFiles(folder, "*", SearchOption.AllDirectories))
            .Where(file => Path.GetExtension(file) is ".cs" or ".razor")
            .Select(file => Path.GetRelativePath(root, file))
            .OrderBy(file => file)
            .ToArray();

        Assert.True(offenders.Length == 0,
            "Account source belongs under Features/Accounts; only the mapped user's CLR namespace is retained:\n" +
            string.Join("\n", offenders));
        Assert.True(File.Exists(Path.Combine(root, "GrumPlates", "Features", "Accounts", "Identity", "ApplicationUser.cs")),
            "The mapped Identity user source belongs to Features/Accounts/Identity.");
    }
}
