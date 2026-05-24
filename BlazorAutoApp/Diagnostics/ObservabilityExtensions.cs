namespace BlazorAutoApp.Diagnostics;

internal static class ObservabilityExtensions
{
    public static void AddAppObservability(this WebApplicationBuilder builder)
    {
        builder.Host.UseSerilog((ctx, _, config) =>
        {
            SelfLog.Enable(m => Console.Error.WriteLine($"[Serilog SelfLog] {m}"));

            config.ReadFrom.Configuration(ctx.Configuration)
                .Enrich.FromLogContext()
                .Enrich.WithEnvironmentName()
                .Enrich.WithProperty("Application", "BlazorAutoApp");

            var hasSeqSink = ctx.Configuration.GetSection("Serilog:WriteTo").GetChildren()
                .Any(c => string.Equals(c["Name"], "Seq", StringComparison.OrdinalIgnoreCase));
            if (ctx.HostingEnvironment.IsEnvironment("Docker") && !hasSeqSink)
            {
                config.WriteTo.Seq("http://seq:5341", period: TimeSpan.FromSeconds(2));
            }
        });
    }

    public static IApplicationBuilder UseAppRequestLogging(this IApplicationBuilder app)
    {
        return app.UseSerilogRequestLogging(options =>
        {
            options.MessageTemplate = "HTTP {RequestMethod} {RequestPath} responded {StatusCode} in {Elapsed:0.0000} ms";
            options.GetLevel = (http, _, ex) =>
            {
                var path = http.Request.Path;
                if (path.StartsWithSegments("/_framework") ||
                    path.StartsWithSegments("/assets") ||
                    string.Equals(path, "/favicon.ico", StringComparison.Ordinal))
                {
                    return LogEventLevel.Verbose;
                }

                return ex is null && http.Response.StatusCode < 500
                    ? LogEventLevel.Information
                    : LogEventLevel.Error;
            };

            options.EnrichDiagnosticContext = (ctx, http) =>
            {
                ctx.Set("RequestId", http.TraceIdentifier);
                ctx.Set("RemoteIp", http.Connection.RemoteIpAddress?.ToString() ?? "");
                ctx.Set("UserName", http.User.Identity?.Name ?? "");
                ctx.Set("QueryString", http.Request.QueryString.HasValue ? http.Request.QueryString.Value : "");
            };
        });
    }
}
