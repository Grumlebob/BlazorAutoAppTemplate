using Microsoft.AspNetCore.StaticFiles;
using Microsoft.Extensions.FileProviders;
using Microsoft.Net.Http.Headers;

namespace BlazorAutoApp.Frontend;

internal static class ReactFrontendHosting
{
    public static void UseStaticFiles(IApplicationBuilder app, IFileProvider fileProvider)
    {
        app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = fileProvider });
        app.UseStaticFiles(new StaticFileOptions { FileProvider = fileProvider });
    }

    public static void MapNavigationFallback(IEndpointRouteBuilder routes, IFileProvider fileProvider)
    {
        routes.MapFallback("{*path:nonfile}", context => ServeNavigationShellAsync(context, fileProvider))
            .ExcludeFromDescription();
    }

    internal static bool IsHtmlNavigation(HttpRequest request)
    {
        if ((!HttpMethods.IsGet(request.Method) && !HttpMethods.IsHead(request.Method))
            || IsReservedPath(request.Path))
        {
            return false;
        }

        var acceptHeader = request.Headers[HeaderNames.Accept].ToString();
        foreach (var value in acceptHeader.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries))
        {
            var parameters = value.Split(';', StringSplitOptions.TrimEntries);
            if (!string.Equals(parameters[0], "text/html", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var qualityParameters = parameters
                .Skip(1)
                .Where(parameter => parameter.StartsWith("q=", StringComparison.OrdinalIgnoreCase))
                .ToArray();
            if (qualityParameters.Length > 1)
            {
                continue;
            }

            var quality = qualityParameters.FirstOrDefault();
            if (quality is null)
            {
                return true;
            }

            if (double.TryParse(
                    quality.AsSpan(2),
                    System.Globalization.NumberStyles.AllowDecimalPoint,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var qualityValue)
                && qualityValue is > 0 and <= 1)
            {
                return true;
            }
        }

        return false;
    }

    private static async Task ServeNavigationShellAsync(HttpContext context, IFileProvider fileProvider)
    {
        if (!IsHtmlNavigation(context.Request))
        {
            context.Response.StatusCode = StatusCodes.Status404NotFound;
            return;
        }

        var shell = fileProvider.GetFileInfo("index.html");
        if (!shell.Exists || shell.IsDirectory)
        {
            context.Response.StatusCode = StatusCodes.Status404NotFound;
            return;
        }

        context.Response.StatusCode = StatusCodes.Status200OK;
        context.Response.ContentType = "text/html; charset=utf-8";
        context.Response.ContentLength = shell.Length;
        context.Response.Headers[HeaderNames.CacheControl] = "no-cache";
        if (HttpMethods.IsHead(context.Request.Method))
        {
            return;
        }

        await using var stream = shell.CreateReadStream();
        await stream.CopyToAsync(context.Response.Body, context.RequestAborted);
    }

    private static bool IsReservedPath(PathString path)
    {
        if (path.StartsWithSegments("/api", StringComparison.OrdinalIgnoreCase)
            || path.StartsWithSegments("/health", StringComparison.OrdinalIgnoreCase)
            || path.StartsWithSegments("/account", StringComparison.OrdinalIgnoreCase)
            || path.StartsWithSegments("/_framework", StringComparison.OrdinalIgnoreCase)
            || path.StartsWithSegments("/_content", StringComparison.OrdinalIgnoreCase)
            || path.StartsWithSegments("/_blazor", StringComparison.OrdinalIgnoreCase)
            || path.StartsWithSegments("/oauth/callback", StringComparison.OrdinalIgnoreCase)
            || path.StartsWithSegments("/oauth2/callback", StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        var firstSegment = path.Value?
            .Split('/', StringSplitOptions.RemoveEmptyEntries)
            .FirstOrDefault();
        return firstSegment?.StartsWith("signin-", StringComparison.OrdinalIgnoreCase) == true;
    }
}
