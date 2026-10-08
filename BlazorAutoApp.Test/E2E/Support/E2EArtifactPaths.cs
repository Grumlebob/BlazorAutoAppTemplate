using System;
using System.IO;

namespace BlazorAutoApp.Test.E2E.Support;

internal static class E2EArtifactPaths
{
    public static string RepositoryRoot { get; } = FindRepositoryRoot();

    public static string RepositoryPath(params string[] segments)
    {
        var pathParts = new string[segments.Length + 1];
        pathParts[0] = RepositoryRoot;
        Array.Copy(segments, 0, pathParts, 1, segments.Length);
        return Path.Combine(pathParts);
    }

    public static string PlaywrightPath(params string[] segments)
    {
        var pathParts = new string[segments.Length + 3];
        pathParts[0] = RepositoryRoot;
        pathParts[1] = "BlazorAutoApp.Test";
        pathParts[2] = Path.Combine("TestResults", "Playwright");
        Array.Copy(segments, 0, pathParts, 3, segments.Length);
        return Path.Combine(pathParts);
    }

    public static string VisualBaselinePath(params string[] segments)
    {
        var pathParts = new string[segments.Length + 3];
        pathParts[0] = RepositoryRoot;
        pathParts[1] = "artifacts";
        pathParts[2] = "visual-baseline";
        Array.Copy(segments, 0, pathParts, 3, segments.Length);
        return Path.Combine(pathParts);
    }

    private static string FindRepositoryRoot()
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

        return AppContext.BaseDirectory;
    }
}
