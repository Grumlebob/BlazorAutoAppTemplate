using System.IO;
using Xunit;
using GrumPlates.Test.TestSupport.Integration;

namespace GrumPlates.Test.E2E.Support;

[Collection(TestCollectionNames.E2E)]
public sealed class E2EArtifactPathsTests
{
    [Fact]
    public void RepositoryRoot_PointsAtSolutionDirectory()
    {
        Assert.True(
            File.Exists(Path.Combine(E2EArtifactPaths.RepositoryRoot, "GrumPlates.sln")),
            $"Expected {E2EArtifactPaths.RepositoryRoot} to contain GrumPlates.sln.");
    }

    [Fact]
    public void ArtifactHelpers_ReturnPathsUnderExpectedRepositoryFolders()
    {
        var playwrightPath = E2EArtifactPaths.PlaywrightPath("Smoke", "shot.png");
        var visualPath = E2EArtifactPaths.VisualBaselinePath("Smoke", "shot.png");

        Assert.EndsWith(
            Path.Combine("GrumPlates.Test", "TestResults", "Playwright", "Smoke", "shot.png"),
            playwrightPath);
        Assert.EndsWith(
            Path.Combine("artifacts", "visual-baseline", "Smoke", "shot.png"),
            visualPath);
    }
}
