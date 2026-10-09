using System.Text.RegularExpressions;
using BlazorAutoApp.Test.Architecture.Support;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

// Repository rules that protect the shared LocalCluster. They fail fast in the
// normal test run when a change (by a person or an agent) breaks one of them.
public sealed class AgentGuardrailTests
{
    private static readonly string RepoRoot = SourceSearch.GetRepoRoot();

    [Fact]
    public void LocalClusterWorkflows_DoNotUseActionsSetupPython()
    {
        var offenders = EnumerateRepoFiles(".github/workflows", "*.yml")
            .Concat(EnumerateRepoFiles(".github/workflows", "*.yaml"))
            .Where(file => Regex.IsMatch(
                File.ReadAllText(file),
                @"uses:\s*actions/setup-python",
                RegexOptions.IgnoreCase))
            .Select(RelativePath)
            .ToList();

        Assert.True(
            offenders.Count == 0,
            "LocalCluster workflows run on self-hosted Linux runners; use python3 -m venv instead of actions/setup-python:\n"
            + string.Join('\n', offenders));
    }

    [Fact]
    public void DotnetBuildAndTest_AreNotInSameWorkflowStep()
    {
        var workflow = ReadRepoFile(".github", "workflows", "ci.yml");
        var buildStep = GetNamedWorkflowStep(workflow, "Build");
        var testStep = GetNamedWorkflowStep(workflow, "Test");

        Assert.Contains("dotnet build --configuration Release --no-restore", buildStep, StringComparison.Ordinal);
        Assert.DoesNotContain("dotnet test", buildStep, StringComparison.Ordinal);
        Assert.Contains("dotnet test --configuration Release --no-build", testStep, StringComparison.Ordinal);
        Assert.DoesNotContain("dotnet build", testStep, StringComparison.Ordinal);
    }

    [Fact]
    public void LocalClusterCd_RequiresSuccessfulCiForSelectedCommit()
    {
        var workflow = ReadRepoFile(".github", "workflows", "cd-localcluster.yml");

        Assert.Contains("find-successful-ci-run.py --target-sha \"$TARGET_SHA\"", workflow, StringComparison.Ordinal);
        Assert.Contains("validate_release_manifest.py", workflow, StringComparison.Ordinal);
        Assert.Contains("--expected-ci-run-attempt \"$CI_RUN_ATTEMPT\"", workflow, StringComparison.Ordinal);
        Assert.Contains("git merge-base --is-ancestor \"$TARGET_SHA\" \"$GITHUB_SHA\"", workflow, StringComparison.Ordinal);
        Assert.Contains("release_image_digest=${RELEASE_IMAGE_DIGEST}", workflow, StringComparison.Ordinal);
    }

    [Fact]
    public void DockerCleanupScripts_DoNotPruneVolumes()
    {
        var script = ReadRepoFile("Deployment", "LocalCluster", "Scripts", "prune-docker-residue.sh");
        var offenders = EnumerateRepoFiles("Deployment/LocalCluster/Scripts", "*.sh")
            .Concat(EnumerateRepoFiles("Deployment/LocalCluster/Scripts", "*.py"))
            .Concat(EnumerateRepoFiles("Deployment/Common/Scripts", "*.sh"))
            .Concat(EnumerateRepoFiles("Deployment/Common/Scripts", "*.py"))
            .Concat(EnumerateRepoFiles(".github/workflows", "*.yml"))
            .Concat(EnumerateRepoFiles("Scripts", "*.ps1"))
            // The deployment audit and the script tests name these commands to forbid them.
            .Where(file => !file.EndsWith("audit_deployment.py", StringComparison.Ordinal)
                && !RelativePath(file).Contains("/Tests/", StringComparison.Ordinal))
            .SelectMany(file => FindMatchingLines(
                file,
                line => Regex.IsMatch(
                    line,
                    @"\bdocker\s+(volume\s+prune|system\s+prune)\b|'volume',\s*'prune'",
                    RegexOptions.CultureInvariant)))
            .ToList();

        Assert.True(
            offenders.Count == 0,
            "Cleanup scripts and workflows must not prune Docker volumes or the whole Docker system:\n" + string.Join('\n', offenders));
        Assert.Contains("Docker volumes are protected", script, StringComparison.Ordinal);
    }

    private static string ReadRepoFile(params string[] parts) =>
        File.ReadAllText(Path.Combine([RepoRoot, .. parts]));

    private static IEnumerable<string> EnumerateRepoFiles(string relativeRoot, string searchPattern)
    {
        var root = Path.Combine(RepoRoot, relativeRoot.Replace('/', Path.DirectorySeparatorChar));
        return Directory.Exists(root)
            ? Directory.EnumerateFiles(root, searchPattern, SearchOption.AllDirectories)
                .Where(file => !IsGeneratedPath(file))
            : [];
    }

    private static string GetNamedWorkflowStep(string workflow, string stepName)
    {
        var match = Regex.Match(
            workflow,
            $@"(?ms)^\s*-\s+name:\s+{Regex.Escape(stepName)}\s*\r?\n(?<body>.*?)(?=^\s*-\s+name:\s+|\z)");

        Assert.True(match.Success, $"Expected workflow step named '{stepName}'.");
        return match.Groups["body"].Value;
    }

    private static IEnumerable<string> FindMatchingLines(
        string file,
        Func<string, bool> predicate)
    {
        var lines = File.ReadAllLines(file);
        for (var index = 0; index < lines.Length; index++)
        {
            if (predicate(lines[index]))
            {
                yield return $"{RelativePath(file)}:{index + 1}: {lines[index].Trim()}";
            }
        }
    }

    private static bool IsGeneratedPath(string file)
    {
        var parts = Path.GetRelativePath(RepoRoot, file)
            .Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return parts.Any(part =>
            part.Equals("bin", StringComparison.OrdinalIgnoreCase)
            || part.Equals("obj", StringComparison.OrdinalIgnoreCase)
            || part.Equals("node_modules", StringComparison.OrdinalIgnoreCase)
            || part.Equals("TestResults", StringComparison.OrdinalIgnoreCase));
    }

    private static string RelativePath(string file) =>
        Path.GetRelativePath(RepoRoot, file).Replace(Path.DirectorySeparatorChar, '/');
}
