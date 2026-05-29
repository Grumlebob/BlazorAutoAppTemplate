using System.Diagnostics;
using BlazorAutoApp.Features.Books;
using Serilog;
using Serilog.Core;
using Serilog.Debugging;
using Serilog.Events;
using OpenTelemetry.Exporter;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Npgsql;

namespace BlazorAutoApp.Infrastructure.Hosting;

internal static class ObservabilityExtensions
{
    private const string OpenTelemetrySectionName = "Observability:OpenTelemetry";

    public static void AddAppObservability(this WebApplicationBuilder builder)
    {
        builder.Host.UseSerilog((ctx, _, config) =>
        {
            SelfLog.Enable(m => Console.Error.WriteLine($"[Serilog SelfLog] {m}"));

            var appName = ctx.Configuration.GetValue<string>("App:Name") ?? "BlazorAutoApp";

            config.ReadFrom.Configuration(ctx.Configuration)
                .Enrich.FromLogContext()
                .Enrich.With(new ActivityLogEventEnricher())
                .Enrich.WithEnvironmentName()
                .Enrich.WithProperty("Application", appName);
        });

        var options = builder.Configuration.GetSection(OpenTelemetrySectionName).Get<AppOpenTelemetryOptions>() ?? new();
        if (!options.Enabled)
        {
            return;
        }

        if (!Uri.TryCreate(options.Endpoint, UriKind.Absolute, out var otlpEndpoint))
        {
            Console.Error.WriteLine($"OpenTelemetry disabled because {OpenTelemetrySectionName}:Endpoint is not an absolute URI.");
            return;
        }

        var appName = builder.Configuration.GetValue<string>("App:Name") ?? "BlazorAutoApp";
        var serviceVersion = typeof(Program).Assembly.GetName().Version?.ToString();
        var serviceInstanceId = Environment.GetEnvironmentVariable("HOSTNAME");
        if (string.IsNullOrWhiteSpace(serviceInstanceId))
        {
            serviceInstanceId = Environment.MachineName;
        }

        var protocol = ParseOtlpProtocol(options.Protocol);
        var sampler = new ParentBasedSampler(new TraceIdRatioBasedSampler(ClampSampleRatio(options.TraceSampleRatio)));

        builder.Services.AddOpenTelemetry()
            .ConfigureResource(resource => resource
                .AddService(
                    serviceName: appName,
                    serviceVersion: serviceVersion,
                    serviceInstanceId: serviceInstanceId)
                .AddAttributes(new Dictionary<string, object>
                {
                    ["deployment.environment.name"] = builder.Environment.EnvironmentName,
                    ["service.namespace"] = "books",
                    ["telemetry.sdk.language"] = "dotnet"
                }))
            .WithTracing(tracing => tracing
                .SetSampler(sampler)
                .AddSource(BooksTelemetry.ActivitySourceName)
                .AddAspNetCoreInstrumentation(instrumentation =>
                {
                    instrumentation.Filter = context => !IsLowValueRequestPath(context.Request.Path);
                    instrumentation.RecordException = true;
                })
                .AddHttpClientInstrumentation(instrumentation =>
                {
                    instrumentation.RecordException = true;
                })
                .AddNpgsql()
                .AddOtlpExporter(exporter => ConfigureOtlpExporter(exporter, otlpEndpoint, protocol, options)))
            .WithMetrics(metrics => metrics
                .AddMeter(BooksTelemetry.MeterName)
                .AddAspNetCoreInstrumentation()
                .AddHttpClientInstrumentation()
                .AddRuntimeInstrumentation()
                .AddNpgsqlInstrumentation()
                .AddOtlpExporter((exporter, reader) =>
                {
                    ConfigureOtlpExporter(exporter, otlpEndpoint, protocol, options);
                    reader.PeriodicExportingMetricReaderOptions.ExportIntervalMilliseconds =
                        Math.Max(1000, options.ExportIntervalMilliseconds);
                    reader.PeriodicExportingMetricReaderOptions.ExportTimeoutMilliseconds =
                        Math.Max(1000, options.ExportTimeoutMilliseconds);
                }));
    }

    public static IApplicationBuilder UseAppRequestLogging(this IApplicationBuilder app)
    {
        return app.UseSerilogRequestLogging(options =>
        {
            options.MessageTemplate = "HTTP {RequestMethod} {RequestPath} responded {StatusCode} in {Elapsed:0.0000} ms";
            options.GetLevel = (http, _, ex) =>
            {
                return GetRequestLogLevel(http, ex);
            };

            options.EnrichDiagnosticContext = (ctx, http) =>
            {
                ctx.Set("RequestId", http.TraceIdentifier);
                ctx.Set("RemoteIp", http.Connection.RemoteIpAddress?.ToString() ?? "");
                ctx.Set("UserName", http.User.Identity?.Name ?? "");
            };
        });
    }

    internal static LogEventLevel GetRequestLogLevel(HttpContext http, Exception? ex)
    {
        if (IsLowValueRequestPath(http.Request.Path))
        {
            return LogEventLevel.Verbose;
        }

        return ex is null && http.Response.StatusCode < 500
            ? LogEventLevel.Information
            : LogEventLevel.Error;
    }

    internal static bool IsLowValueRequestPath(PathString path)
    {
        if (path.StartsWithSegments("/health") ||
            path.StartsWithSegments("/_framework") ||
            path.StartsWithSegments("/assets") ||
            string.Equals(path, "/favicon.ico", StringComparison.Ordinal))
        {
            return true;
        }

        var value = path.Value;
        if (string.IsNullOrEmpty(value))
        {
            return false;
        }

        return value.EndsWith(".css", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".js", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".map", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".png", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".jpg", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".jpeg", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".svg", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".webp", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".woff", StringComparison.OrdinalIgnoreCase) ||
            value.EndsWith(".woff2", StringComparison.OrdinalIgnoreCase);
    }

    private static void ConfigureOtlpExporter(
        OtlpExporterOptions exporter,
        Uri endpoint,
        OtlpExportProtocol protocol,
        AppOpenTelemetryOptions options)
    {
        exporter.Endpoint = endpoint;
        exporter.Protocol = protocol;
        exporter.TimeoutMilliseconds = Math.Max(1000, options.ExportTimeoutMilliseconds);
    }

    private static OtlpExportProtocol ParseOtlpProtocol(string? protocol)
    {
        return string.Equals(protocol, "HttpProtobuf", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(protocol, "Http", StringComparison.OrdinalIgnoreCase)
                ? OtlpExportProtocol.HttpProtobuf
                : OtlpExportProtocol.Grpc;
    }

    private static double ClampSampleRatio(double sampleRatio)
    {
        if (double.IsNaN(sampleRatio))
        {
            return 0.1;
        }

        return Math.Clamp(sampleRatio, 0.0, 1.0);
    }

    private sealed class ActivityLogEventEnricher : ILogEventEnricher
    {
        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            var activity = Activity.Current;
            if (activity is null)
            {
                return;
            }

            logEvent.AddPropertyIfAbsent(propertyFactory.CreateProperty("TraceId", activity.TraceId.ToString()));
            logEvent.AddPropertyIfAbsent(propertyFactory.CreateProperty("SpanId", activity.SpanId.ToString()));
        }
    }

    private sealed class AppOpenTelemetryOptions
    {
        public bool Enabled { get; init; }

        public string Endpoint { get; init; } = "http://localhost:4317";

        public string Protocol { get; init; } = "Grpc";

        public double TraceSampleRatio { get; init; } = 0.1;

        public int ExportIntervalMilliseconds { get; init; } = 10000;

        public int ExportTimeoutMilliseconds { get; init; } = 5000;
    }
}
