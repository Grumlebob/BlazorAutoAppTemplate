using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.StaticFiles;
using Microsoft.Extensions.FileProviders;
using Microsoft.Net.Http.Headers;

namespace BlazorAutoApp.Frontend;

internal static class ReactFrontendHosting
{
    private static readonly Regex InlineScriptPattern = new(
        "<script\\b(?<attributes>[^>]*)>(?<body>.*?)</script\\s*>",
        RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.Singleline | RegexOptions.CultureInvariant);
    private static readonly Regex ScriptSourcePattern = new(
        "\\bsrc\\s*=",
        RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    internal const string ContentSecurityPolicy =
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'";

    public static void UseSecurityHeaders(IApplicationBuilder app, IFileProvider? fileProvider = null)
    {
        var contentSecurityPolicy = GetContentSecurityPolicy(fileProvider);
        app.Use(async (context, next) =>
        {
            var headers = context.Response.Headers;
            headers["Content-Security-Policy"] = contentSecurityPolicy;
            headers["X-Content-Type-Options"] = "nosniff";
            headers["X-Frame-Options"] = "DENY";
            headers["Referrer-Policy"] = "strict-origin-when-cross-origin";
            headers["Permissions-Policy"] = "local-network-access=()";

            await next();
        });
    }

    internal static string GetContentSecurityPolicy(IFileProvider? fileProvider)
    {
        if (fileProvider is null)
        {
            return ContentSecurityPolicy;
        }

        var shell = fileProvider.GetFileInfo("index.html");
        if (!shell.Exists || shell.IsDirectory)
        {
            return ContentSecurityPolicy;
        }

        using var stream = shell.CreateReadStream();
        using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        var html = reader.ReadToEnd();
        var hashes = InlineScriptPattern.Matches(html)
            .Cast<Match>()
            .Where(match => !ScriptSourcePattern.IsMatch(match.Groups["attributes"].Value))
            .Select(match => Convert.ToBase64String(SHA256.HashData(Encoding.UTF8.GetBytes(match.Groups["body"].Value))))
            .Distinct(StringComparer.Ordinal)
            .ToArray();
        if (hashes.Length == 0)
        {
            return ContentSecurityPolicy;
        }

        var hashSources = string.Join(' ', hashes.Select(hash => $"'sha256-{hash}'"));
        return ContentSecurityPolicy.Replace(
            "script-src 'self'",
            $"script-src 'self' {hashSources}",
            StringComparison.Ordinal);
    }

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
