using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Microsoft.AspNetCore.Components;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class HttpClientUsageTests
{
    private static string GetRepoRoot()
    {
        // Walk up from test bin folder until we find the solution file
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "BlazorAutoApp.sln")))
        {
            dir = dir.Parent;
        }
        return dir?.FullName ?? AppContext.BaseDirectory;
    }

    private static IEnumerable<string> Grep(string root, string search, string searchIn, params string[] extensions)
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

    [Fact]
    public void ServerAssembly_HasNo_HttpClient_InjectionOrSurface()
    {
        var server = typeof(BlazorAutoApp.Features.Movies.MoviesServerService).Assembly;
        var offenders = new List<string>();

        foreach (var t in server.GetTypes())
        {
            // Fields
            foreach (var f in t.GetFields(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
                if (ContainsHttpClient(f.FieldType)) offenders.Add($"{t.FullName} field {f.Name}");

            // Properties
            foreach (var p in t.GetProperties(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
                if (ContainsHttpClient(p.PropertyType)) offenders.Add($"{t.FullName} property {p.Name}");

            // Methods
            foreach (var m in t.GetMethods(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (ContainsHttpClient(m.ReturnType)) offenders.Add($"{t.FullName} method {m.Name} return");
                foreach (var param in m.GetParameters())
                    if (ContainsHttpClient(param.ParameterType)) offenders.Add($"{t.FullName} method {m.Name} param {param.Name}");
            }

            // Constructors
            foreach (var c in t.GetConstructors(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
                foreach (var param in c.GetParameters())
                    if (ContainsHttpClient(param.ParameterType)) offenders.Add($"{t.FullName} ctor param {param.Name}");
        }

        if (offenders.Count > 0)
        {
            // Add source hints (file:line) from the server project
            var root = GetRepoRoot();
            var hints = Grep(root, "HttpClient", "BlazorAutoApp").ToList();
            var msg = "Server must not use HttpClient directly:\n"
                      + string.Join("\n", offenders)
                      + (hints.Count > 0 ? "\n\nSource locations containing 'HttpClient':\n" + string.Join("\n", hints) : string.Empty);
            Assert.True(false, msg);
        }
    }

    private static bool ContainsHttpClient(Type? type)
    {
        if (type is null) return false;
        if (type.FullName == "System.Net.Http.HttpClient") return true;
        if (type.IsGenericType) return type.GetGenericArguments().Any(ContainsHttpClient);
        if (type.HasElementType) return ContainsHttpClient(type.GetElementType());
        return false;
    }

    [Fact]
    public void BlazorComponents_DoNotInject_HttpClient()
    {
        var client = typeof(BlazorAutoApp.Client.Services.MoviesClientService).Assembly;
        var offenders = new List<string>();
        var componentType = typeof(ComponentBase);
        const string injectAttrName = "InjectAttribute";

        foreach (var t in client.GetTypes().Where(tt => componentType.IsAssignableFrom(tt)))
        {
            foreach (var p in t.GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                var hasInject = p.GetCustomAttributes(inherit: true).Any(a => a.GetType().Name == injectAttrName);
                if (hasInject && p.PropertyType.FullName == "System.Net.Http.HttpClient")
                    offenders.Add($"{t.FullName} property {p.Name}");
            }
        }

        if (offenders.Count > 0)
        {
            // Add source hints (file:line) from the client project (.razor + .razor.cs)
            var root = GetRepoRoot();
            var hints = Grep(root, "@inject HttpClient", "BlazorAutoApp.Client", ".razor").ToList();
            // Also code-behind
            hints.AddRange(Grep(root, "[Inject]", "BlazorAutoApp.Client", ".cs").Where(h => h.Contains("HttpClient", StringComparison.OrdinalIgnoreCase)));

            var msg = "Blazor components must not inject HttpClient directly:\n"
                      + string.Join("\n", offenders)
                      + (hints.Count > 0 ? "\n\nSource locations:\n" + string.Join("\n", hints.Distinct()) : string.Empty);
            Assert.True(false, msg);
        }
    }
}

