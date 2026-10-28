using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.StaticFiles;
using Microsoft.AspNetCore.ResponseCompression;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Net.Http.Headers;

namespace GrumPlates.Frontend;

internal static partial class ReactFrontendHosting
{
    private const string SpaFallbackFileName = "__spa-fallback.html";
    private const int RegexTimeoutMilliseconds = 1000;

    [GeneratedRegex(
        "<script\\b(?<attributes>[^>]*)>(?<body>.*?)</script\\s*>",
        RegexOptions.IgnoreCase | RegexOptions.Singleline | RegexOptions.CultureInvariant,
        RegexTimeoutMilliseconds)]
    private static partial Regex InlineScriptPattern();

    [GeneratedRegex("\\bsrc\\s*=", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant, RegexTimeoutMilliseconds)]
    private static partial Regex ScriptSourcePattern();

    // The request path is client-controlled, so the match is bounded.
    [GeneratedRegex("-[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9]{1,10}$", RegexOptions.CultureInvariant, RegexTimeoutMilliseconds)]
    private static partial Regex FingerprintedAssetPattern();

    internal const string ContentSecurityPolicy =
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'";

    internal const string CrossOriginOpenerPolicy = "same-origin";
    internal const string CrossOriginResourcePolicy = "same-site";
    internal const string PermissionsPolicy =
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), local-network-access=()";

    public static void AddResponseCompression(IServiceCollection services)
    {
        services.AddResponseCompression(options =>
        {
            options.EnableForHttps = true;
            options.MimeTypes = ResponseCompressionDefaults.MimeTypes
                .Concat(["text/javascript", "image/svg+xml"])
                .ToArray();
        });
    }

    public static void UseSecurityHeaders(IApplicationBuilder app, IFileProvider? fileProvider = null)
    {
        var contentSecurityPolicy = GetContentSecurityPolicy(fileProvider);
        app.Use(async (context, next) =>
        {
            var headers = context.Response.Headers;
            headers.ContentSecurityPolicy = contentSecurityPolicy;
            context.Response.OnStarting(() =>
            {
                // The shell and static HTML set their content type later in the pipeline.
                if (context.Response.ContentType?.StartsWith("text/html", StringComparison.OrdinalIgnoreCase) == true)
                {
                    headers.ContentSecurityPolicy = WithScriptNonce(contentSecurityPolicy);
                }

                return Task.CompletedTask;
            });
            headers.XContentTypeOptions = "nosniff";
            headers.XFrameOptions = "DENY";
            headers["Referrer-Policy"] = "strict-origin-when-cross-origin";
            headers["Permissions-Policy"] = PermissionsPolicy;
            headers["Cross-Origin-Opener-Policy"] = CrossOriginOpenerPolicy;
            headers["Cross-Origin-Resource-Policy"] = CrossOriginResourcePolicy;
            if (context.Request.Path.StartsWithSegments("/api/books", StringComparison.OrdinalIgnoreCase))
            {
                headers[HeaderNames.CacheControl] = "private, no-store";
            }

            await next();
        });
    }

    internal static string GetContentSecurityPolicy(IFileProvider? fileProvider)
    {
        if (fileProvider is null)
        {
            return ContentSecurityPolicy;
        }

        var hashes = new HashSet<string>(StringComparer.Ordinal);
        foreach (var fileName in new[] { "index.html", SpaFallbackFileName })
        {
            var shell = fileProvider.GetFileInfo(fileName);
            if (!shell.Exists || shell.IsDirectory)
            {
                continue;
            }

            using var stream = shell.CreateReadStream();
            using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
            var html = reader.ReadToEnd();
            foreach (Match match in InlineScriptPattern().Matches(html))
            {
                if (ScriptSourcePattern().IsMatch(match.Groups["attributes"].Value))
                {
                    continue;
                }

                hashes.Add(Convert.ToBase64String(SHA256.HashData(Encoding.UTF8.GetBytes(match.Groups["body"].Value))));
            }
        }

        if (hashes.Count == 0)
        {
            return ContentSecurityPolicy;
        }

        var hashSources = string.Join(' ', hashes.Select(hash => $"'sha256-{hash}'"));
        return ContentSecurityPolicy.Replace(
            "script-src 'self'",
            $"script-src 'self' {hashSources}",
            StringComparison.Ordinal);
    }

    /// <summary>
    /// Adds a fresh random nonce to a document's script-src. Our own markup never uses it:
    /// its inline scripts stay authorized by exact hashes. Cloudflare's JavaScript detections
    /// read the nonce from this header and put it on the script they inject, so bot detection
    /// runs without 'unsafe-inline'. A new nonce per response keeps it unpredictable.
    /// </summary>
    internal static string WithScriptNonce(string policy)
    {
        var nonce = Convert.ToBase64String(RandomNumberGenerator.GetBytes(16));
        return policy.Replace("script-src 'self'", $"script-src 'self' 'nonce-{nonce}'", StringComparison.Ordinal);
    }

    public static void UseStaticFiles(IApplicationBuilder app, IFileProvider fileProvider)
    {
        app.UseResponseCompression();
        app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = fileProvider });
        app.UseStaticFiles(new StaticFileOptions
        {
            FileProvider = fileProvider,
            OnPrepareResponse = context =>
            {
                var path = context.Context.Request.Path.Value ?? string.Empty;
                context.Context.Response.Headers[HeaderNames.CacheControl] = FingerprintedAssetPattern().IsMatch(path)
                    ? "public,max-age=31536000,immutable"
                    : "no-cache";
            }
        });
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

        var isRootNavigation = string.IsNullOrEmpty(context.Request.Path.Value)
            || string.Equals(context.Request.Path.Value, "/", StringComparison.Ordinal);
        var shell = fileProvider.GetFileInfo(isRootNavigation ? "index.html" : SpaFallbackFileName);
        if (!shell.Exists || shell.IsDirectory)
        {
            shell = fileProvider.GetFileInfo("index.html");
        }

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
