using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace BlazorAutoApp.Test.Architecture.Support;

internal static class SourceSearch
{
    public static string GetRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "BlazorAutoApp.sln")))
        {
            dir = dir.Parent;
        }
        return dir?.FullName ?? AppContext.BaseDirectory;
    }

    public static IEnumerable<string> Grep(string root, string search, string searchIn, params string[] extensions)
    {
        var folder = Path.Combine(root, searchIn);
        if (!Directory.Exists(folder)) yield break;
        var exts = extensions.Length == 0 ? [".cs", ".razor"] : extensions;
        foreach (var file in Directory.EnumerateFiles(folder, "*.*", SearchOption.AllDirectories)
                                       .Where(f => exts.Contains(Path.GetExtension(f), StringComparer.OrdinalIgnoreCase))
                                       .Where(f => !IsGeneratedPath(root, f)))
        {
            var lines = File.ReadAllLines(file);
            for (int i = 0; i < lines.Length; i++)
            {
                if (lines[i].Contains(search, StringComparison.OrdinalIgnoreCase))
                    yield return $"{Path.GetRelativePath(root, file)}:{i + 1}: {lines[i].Trim()}";
            }
        }
    }

    public static IEnumerable<string> FindTypeHints(string root, string projectFolder, Type t)
        => Grep(root, $"class {t.Name}", projectFolder, ".cs")
            .Concat(Grep(root, t.Namespace ?? string.Empty, projectFolder, ".cs"))
            .Distinct();

    private static bool IsGeneratedPath(string root, string file)
    {
        var relative = Path.GetRelativePath(root, file)
            .Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return relative.Any(part =>
            part.Equals("bin", StringComparison.OrdinalIgnoreCase) ||
            part.Equals("obj", StringComparison.OrdinalIgnoreCase) ||
            part.Equals("node_modules", StringComparison.OrdinalIgnoreCase) ||
            part.Equals("TestResults", StringComparison.OrdinalIgnoreCase));
    }
}
