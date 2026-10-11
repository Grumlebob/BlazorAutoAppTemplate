using Microsoft.Extensions.FileProviders;

namespace BlazorAutoApp.Frontend;

internal sealed class ReactFrontendStaticRoot : IDisposable
{
    public ReactFrontendStaticRoot(IWebHostEnvironment environment, IConfiguration configuration)
        : this(ResolvePath(environment, configuration))
    {
    }

    internal ReactFrontendStaticRoot(string path)
    {
        Path = System.IO.Path.GetFullPath(path);
        if (!Directory.Exists(Path))
        {
            throw new InvalidOperationException($"The selected React static root does not exist: '{Path}'.");
        }

        FileProvider = new PhysicalFileProvider(Path);
    }

    public string Path { get; }

    public IFileProvider FileProvider { get; }

    public void Dispose() => (FileProvider as IDisposable)?.Dispose();

    private static string ResolvePath(IWebHostEnvironment environment, IConfiguration configuration)
    {
        if (environment.IsDevelopment()
            && !string.IsNullOrWhiteSpace(configuration["Frontend:React:StaticRoot"]))
        {
            var repositoryRoot = System.IO.Path.GetFullPath(
                System.IO.Path.Combine(environment.ContentRootPath, ".."));
            var configuredPath = System.IO.Path.GetFullPath(
                configuration["Frontend:React:StaticRoot"]!,
                environment.ContentRootPath);
            var comparison = OperatingSystem.IsWindows()
                ? StringComparison.OrdinalIgnoreCase
                : StringComparison.Ordinal;
            var repositoryPrefix = System.IO.Path.TrimEndingDirectorySeparator(repositoryRoot)
                + System.IO.Path.DirectorySeparatorChar;
            if (!configuredPath.StartsWith(repositoryPrefix, comparison))
            {
                throw new InvalidOperationException(
                    "Frontend:React:StaticRoot must resolve within the repository in Development.");
            }

            return configuredPath;
        }

        return environment.IsDevelopment()
            ? System.IO.Path.Combine(environment.ContentRootPath, "Frontend", "React", "wwwroot")
            : System.IO.Path.Combine(environment.ContentRootPath, "wwwroot");
    }
}
