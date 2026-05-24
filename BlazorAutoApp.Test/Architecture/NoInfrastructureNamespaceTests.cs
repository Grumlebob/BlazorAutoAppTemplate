using System;
using System.Linq;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class NoInfrastructureNamespaceTests
{
    [Fact]
    public void ServerAssembly_HasNo_Infrastructure_Namespace()
    {
        var offendingTypes = ArchitectureAssemblies.Server.GetTypes()
            .Where(t => t.Namespace != null && t.Namespace.Split('.').Contains("Infrastructure", StringComparer.Ordinal))
            .ToList();

        var offending = offendingTypes.Select(t => t.FullName).ToList();
        if (offending.Count > 0)
        {
            var root = SourceSearch.GetRepoRoot();
            var hints = offendingTypes.SelectMany(t => SourceSearch.FindTypeHints(root, "BlazorAutoApp", t)).ToList();
            var msg = "Found types under an Infrastructure namespace:\n" + string.Join("\n", offending)
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
}
