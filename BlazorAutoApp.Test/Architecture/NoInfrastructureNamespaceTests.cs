using System;
using System.IO;
using System.Linq;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class NoInfrastructureNamespaceTests
{
    [Fact]
    public void ServerAssembly_Infrastructure_Namespaces_Are_PlatformOnly()
    {
        var offendingTypes = ArchitectureAssemblies.Server.GetTypes()
            .Where(t => t.Namespace != null && t.Namespace.Split('.').Contains("Infrastructure", StringComparer.Ordinal))
            .Where(t => !t.Namespace!.StartsWith("BlazorAutoApp.Infrastructure.Hosting", StringComparison.Ordinal)
                     && !t.Namespace.StartsWith("BlazorAutoApp.Infrastructure.Persistence", StringComparison.Ordinal))
            .ToList();

        var offending = offendingTypes.Select(t => t.FullName).ToList();
        if (offending.Count > 0)
        {
            var root = SourceSearch.GetRepoRoot();
            var hints = offendingTypes.SelectMany(t => SourceSearch.FindTypeHints(root, "BlazorAutoApp", t)).ToList();
            var msg = "Found server Infrastructure types outside the approved platform folders:\n" + string.Join("\n", offending)
                      + (hints.Count > 0 ? "\n\nSource locations:\n" + string.Join("\n", hints) : string.Empty);
            Assert.Fail(msg);
        }
    }

    [Fact]
    public void ClientAssembly_HasNo_Infrastructure_Namespace()
    {
        var offendingTypes = ArchitectureAssemblies.Client.GetTypes()
            .Where(t => t.Namespace != null && t.Namespace.Split('.').Contains("Infrastructure", StringComparer.Ordinal))
            .ToList();

        var offending = offendingTypes.Select(t => t.FullName).ToList();
        if (offending.Count > 0)
        {
            var root = SourceSearch.GetRepoRoot();
            var hints = offendingTypes.SelectMany(t => SourceSearch.FindTypeHints(root, "BlazorAutoApp.Client", t)).ToList();
            var msg = "Found types under an Infrastructure namespace in client:\n" + string.Join("\n", offending)
                      + (hints.Count > 0 ? "\n\nSource locations:\n" + string.Join("\n", hints) : string.Empty);
            Assert.Fail(msg);
        }
    }

    [Fact]
    public void CoreAssembly_HasNo_Infrastructure_Namespace()
    {
        var offendingTypes = ArchitectureAssemblies.Core.GetTypes()
            .Where(t => t.Namespace != null && t.Namespace.Split('.').Contains("Infrastructure", StringComparer.Ordinal))
            .ToList();

        var offending = offendingTypes.Select(t => t.FullName).ToList();
        if (offending.Count > 0)
        {
            var root = SourceSearch.GetRepoRoot();
            var hints = offendingTypes.SelectMany(t => SourceSearch.FindTypeHints(root, "BlazorAutoApp.Core", t)).ToList();
            var msg = "Found types under an Infrastructure namespace in core:\n" + string.Join("\n", offending)
                      + (hints.Count > 0 ? "\n\nSource locations:\n" + string.Join("\n", hints) : string.Empty);
            Assert.Fail(msg);
        }
    }

    [Fact]
    public void ServerProject_HasNo_Legacy_Root_Infrastructure_Folders()
    {
        var serverRoot = Path.Combine(SourceSearch.GetRepoRoot(), "BlazorAutoApp");
        var legacyFolders = new[] { "Caching", "Configuration", "Data", "Diagnostics", "Security", "Storage" };
        var existing = legacyFolders
            .Select(folder => Path.Combine(serverRoot, folder))
            .Where(Directory.Exists)
            .Select(path => Path.GetRelativePath(SourceSearch.GetRepoRoot(), path))
            .OrderBy(path => path)
            .ToList();

        Assert.True(existing.Count == 0,
            "Legacy root infrastructure/runtime folders should stay consolidated or generated outside source:\n"
            + string.Join("\n", existing));
    }
}
