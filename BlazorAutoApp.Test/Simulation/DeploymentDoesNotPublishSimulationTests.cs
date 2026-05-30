using Xunit;

namespace BlazorAutoApp.Test.Simulation;

public sealed class DeploymentDoesNotPublishSimulationTests
{
    [Fact]
    public void DockerfilePublishesOnlyWebApp()
    {
        var root = FindRepoRoot();
        var dockerfile = File.ReadAllText(Path.Combine(root, "BlazorAutoApp", "Dockerfile"));

        Assert.DoesNotContain("BlazorAutoApp.Simulation", dockerfile, StringComparison.Ordinal);
        Assert.Contains("dotnet publish ./BlazorAutoApp/BlazorAutoApp.csproj", dockerfile, StringComparison.Ordinal);
        Assert.Contains("dotnet restore ./BlazorAutoApp/BlazorAutoApp.csproj", dockerfile, StringComparison.Ordinal);
    }

    [Fact]
    public void DockerIgnoreExcludesSimulation()
    {
        var root = FindRepoRoot();
        var dockerignore = File.ReadAllText(Path.Combine(root, ".dockerignore"));

        Assert.Contains("BlazorAutoApp.Simulation/**", dockerignore, StringComparison.Ordinal);
        Assert.Contains("Tools/**", dockerignore, StringComparison.Ordinal);
    }

    [Fact]
    public void CiBuildsOnlyWebAppDockerfile()
    {
        var root = FindRepoRoot();
        var ci = File.ReadAllText(Path.Combine(root, ".github", "workflows", "ci.yml"));

        Assert.Contains("-f BlazorAutoApp/Dockerfile", ci, StringComparison.Ordinal);
        Assert.DoesNotContain("BlazorAutoApp.Simulation/Dockerfile", ci, StringComparison.Ordinal);
        Assert.DoesNotContain("dotnet publish BlazorAutoApp.Simulation", ci, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("cd-localcluster.yml")]
    [InlineData("cd-cloud.yml")]
    public void CdWorkflowsDoNotDeploySimulation(string workflowFile)
    {
        var root = FindRepoRoot();
        var workflow = File.ReadAllText(Path.Combine(root, ".github", "workflows", workflowFile));

        Assert.DoesNotContain("BlazorAutoApp.Simulation", workflow, StringComparison.Ordinal);
        Assert.DoesNotContain("RunSimulation", workflow, StringComparison.Ordinal);
    }

    [Fact]
    public void DeploymentAssetsDoNotMentionSimulation()
    {
        var deploymentRoot = Path.Combine(FindRepoRoot(), "Deployment");
        var offenders = Directory
            .EnumerateFiles(deploymentRoot, "*", SearchOption.AllDirectories)
            .Where(static path => !path.Contains($"{Path.DirectorySeparatorChar}.terraform{Path.DirectorySeparatorChar}", StringComparison.Ordinal))
            .Where(static path => IsTextFile(path))
            .Where(path => File.ReadAllText(path).Contains("BlazorAutoApp.Simulation", StringComparison.Ordinal))
            .Select(path => Path.GetRelativePath(deploymentRoot, path))
            .ToArray();

        Assert.Empty(offenders);
    }

    [Theory]
    [InlineData("BlazorAutoApp", "BlazorAutoApp.csproj")]
    [InlineData("BlazorAutoApp.Client", "BlazorAutoApp.Client.csproj")]
    [InlineData("BlazorAutoApp.Core", "BlazorAutoApp.Core.csproj")]
    public void ProductionProjectsDoNotReferenceSimulation(string directory, string projectFile)
    {
        var root = FindRepoRoot();
        var project = File.ReadAllText(Path.Combine(root, directory, projectFile));

        Assert.DoesNotContain("BlazorAutoApp.Simulation", project, StringComparison.Ordinal);
    }

    private static bool IsTextFile(string path)
    {
        var extension = Path.GetExtension(path);
        return extension is ".yml" or ".yaml" or ".j2" or ".sh" or ".ps1" or ".json" or ".env" or ".tf" or ".md";
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
