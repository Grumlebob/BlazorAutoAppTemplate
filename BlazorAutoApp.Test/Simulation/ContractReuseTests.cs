using System.Text.RegularExpressions;
using Xunit;

namespace BlazorAutoApp.Test.Simulation;

public sealed class ContractReuseTests
{
    [Fact]
    public void SimulationDoesNotDefineDuplicatedBookApiContracts()
    {
        var simulationRoot = Path.Combine(FindRepoRoot(), "BlazorAutoApp.Simulation");
        var duplicatePattern = new Regex(
            @"\b(class|record)\s+(GetBooksResponse|BookItem|CreateBookRequest|CreateBookResponse|UpdateBookRequest|AuthorBooksResponse|AuthorBookItem)\b",
            RegexOptions.Compiled);

        var offenders = Directory
            .EnumerateFiles(simulationRoot, "*.cs", SearchOption.AllDirectories)
            .Where(static path => !path.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}", StringComparison.Ordinal)
                && !path.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}", StringComparison.Ordinal))
            .SelectMany(path => duplicatePattern
                .Matches(File.ReadAllText(path))
                .Select(match => $"{Path.GetRelativePath(simulationRoot, path)}: {match.Value}"))
            .ToArray();

        Assert.Empty(offenders);
    }

    [Fact]
    public void SimulationReferencesCoreContracts()
    {
        var projectPath = Path.Combine(FindRepoRoot(), "BlazorAutoApp.Simulation", "BlazorAutoApp.Simulation.csproj");
        var project = File.ReadAllText(projectPath).Replace('/', '\\');

        Assert.Contains(@"..\BlazorAutoApp.Core\BlazorAutoApp.Core.csproj", project);
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "BlazorAutoApp.sln")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new InvalidOperationException("Could not find repository root.");
    }
}
