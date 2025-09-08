using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace BlazorAutoApp.Test.Architecture;

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
        var exts = extensions.Length == 0 ? new[] { ".cs", ".razor" } : extensions;
        foreach (var file in Directory.EnumerateFiles(folder, "*.*", SearchOption.AllDirectories)
                                       .Where(f => exts.Contains(Path.GetExtension(f), StringComparer.OrdinalIgnoreCase)))
        {
            var lines = File.ReadAllLines(file);
            for (int i = 0; i < lines.Length; i++)
            {
                if (lines[i].IndexOf(search, StringComparison.OrdinalIgnoreCase) >= 0)
                    yield return $"{Path.GetRelativePath(root, file)}:{i + 1}: {lines[i].Trim()}";
            }
        }
    }

    public static IEnumerable<string> FindTypeHints(string root, string projectFolder, Type t)
        => Grep(root, $"class {t.Name}", projectFolder, ".cs")
            .Concat(Grep(root, t.Namespace ?? string.Empty, projectFolder, ".cs"))
            .Distinct();
}

