using BlazorAutoApp.Components;
using BlazorAutoApp.Data;
using BlazorAutoApp.Features.Movies;
using Microsoft.EntityFrameworkCore;
using BlazorAutoApp.Core.Features.Movies;
using Serilog;
using Serilog.Events;
using Serilog.Debugging;
using System.Linq;
using Microsoft.Extensions.Caching.Hybrid;
using Microsoft.Extensions.Options;

var builder = WebApplication.CreateBuilder(args);

// Optional: include Docker-specific configuration when running in containers
if (builder.Environment.IsEnvironment("Docker"))
{
    builder.Configuration.AddJsonFile("appsettings.Docker.json", optional: true);
}

// SERILOG CONFIGURATION ---
builder.Host.UseSerilog((ctx, services, config) =>
{
    // Surface sink errors if anything goes wrong
    SelfLog.Enable(m => Console.Error.WriteLine($"[Serilog SelfLog] {m}"));

    // Prefer configuration-driven setup (appsettings.json + appsettings.Docker.json)
    config.ReadFrom.Configuration(ctx.Configuration)
          .Enrich.FromLogContext()
          .Enrich.WithEnvironmentName()
          .Enrich.WithProperty("Application", "BlazorAutoApp");

    // Tighten: if running in Docker and the configuration didn't add a Seq sink, add a safe default
    var hasSeqSink = ctx.Configuration.GetSection("Serilog:WriteTo").GetChildren()
        .Any(c => string.Equals(c["Name"], "Seq", StringComparison.OrdinalIgnoreCase));
    if (ctx.HostingEnvironment.IsEnvironment("Docker") && !hasSeqSink)
    {
        Console.WriteLine("[Startup] No Seq sink found in configuration; adding default http://seq:5341 for Docker.");
        config.WriteTo.Seq("http://seq:5341", period: TimeSpan.FromSeconds(2));
    }
});


// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents()
    .AddInteractiveWebAssemblyComponents();

// EF Core with PostgreSQL
// Use DefaultConnection (overridden by Docker environment via appsettings.Docker.json)
var connString = builder.Configuration.GetConnectionString("DefaultConnection")
                 ?? "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres";

builder.Services.AddDbContext<AppDbContext>(options => options.UseNpgsql(connString));

// Movies service for server-side prerendering
builder.Services.AddScoped<IMoviesApi, MoviesServerService>();
builder.Services.Configure<BlazorAutoApp.Features.Movies.MoviesCacheOptions>(
    builder.Configuration.GetSection("Cache:Movies"));

// Redis (distributed cache) + Hybrid cache
var redisConn = builder.Configuration.GetSection("Redis").GetValue<string>("Configuration") ?? "localhost:6379";
builder.Services.AddStackExchangeRedisCache(options => { options.Configuration = redisConn; });
builder.Services.AddHybridCache();

var app = builder.Build();

// Concise per-request logging
app.UseSerilogRequestLogging(options =>
{
    options.MessageTemplate = "HTTP {RequestMethod} {RequestPath} responded {StatusCode} in {Elapsed:0.0000} ms";

    // Adjust log level (e.g., demote health checks)
    options.GetLevel = (http, elapsed, ex) =>
    {
        var path = http.Request.Path;
        if (path.StartsWithSegments("/_framework") || path.StartsWithSegments("/assets") || string.Equals(path, "/favicon.ico", StringComparison.Ordinal))
            return LogEventLevel.Verbose;
        return ex is null && http.Response.StatusCode < 500 ? LogEventLevel.Information : LogEventLevel.Error;
    };

    // Attach common properties
    options.EnrichDiagnosticContext = (ctx, http) =>
    {
        ctx.Set("RequestId", http.TraceIdentifier);
        ctx.Set("RemoteIp", http.Connection.RemoteIpAddress?.ToString() ?? "");
        ctx.Set("UserName", http.User?.Identity?.Name ?? "");
        ctx.Set("QueryString", http.Request.QueryString.HasValue ? http.Request.QueryString.Value : "");
    };
});


// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseWebAssemblyDebugging();
}
else
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseHttpsRedirection();

app.UseAntiforgery();

// Apply EF Core migrations at startup
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.Migrate();
}

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode()
    .AddInteractiveWebAssemblyRenderMode()
    .AddAdditionalAssemblies(typeof(BlazorAutoApp.Client._Imports).Assembly);

// Minimal API endpoints
app.MapMovieEndpoints();

app.Run();

//A hacky solution to use Testcontainers with WebApplication.CreateBuilder for integration tests
public partial class Program;
