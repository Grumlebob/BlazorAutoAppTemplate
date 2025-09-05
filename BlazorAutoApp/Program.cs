using BlazorAutoApp.Components;
using BlazorAutoApp.Data;
using BlazorAutoApp.Features.Movies;
using Microsoft.EntityFrameworkCore;
using BlazorAutoApp.Core.Features.Movies;
using Serilog;
using Serilog.Events;

var builder = WebApplication.CreateBuilder(args);

// Optional: include Docker-specific configuration when running in containers
if (builder.Environment.IsEnvironment("Docker"))
{
    builder.Configuration.AddJsonFile("appsettings.Docker.json", optional: true);
}

// SERILOG CONFIGURATION ---

builder.Host.UseSerilog((ctx, services, config) =>
{
    // Start with a clean configuration, defining everything explicitly here.
    config
        .MinimumLevel.Information()
        .MinimumLevel.Override("Microsoft", LogEventLevel.Warning)
        .MinimumLevel.Override("System", LogEventLevel.Warning)
        .Enrich.FromLogContext()
        .Enrich.WithProperty("Application", "BlazorAutoApp")
        .Enrich.WithEnvironmentName()
        .WriteTo.Console(); // Always write to the console for local debugging.

    // Get the Seq server URL injected by .NET Aspire
    var seqServerUrl = ctx.Configuration["Seq:ServerUrl"];

    // Check if the URL is available and add the Seq sink
    if (!string.IsNullOrEmpty(seqServerUrl))
    {
        // Use WriteLine here for startup diagnostics, as logging might not be fully initialized.
        Console.WriteLine($"[Startup] Sending logs to Seq at: {seqServerUrl}");
        config.WriteTo.Seq(
            serverUrl: seqServerUrl,
            period: TimeSpan.FromSeconds(2));
    }
    else
    {
        Console.WriteLine("[Startup] Seq:ServerUrl not found. Seq logging is disabled.");
    }
});


// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents()
    .AddInteractiveWebAssemblyComponents();

// EF Core with PostgreSQL
// Prefer Aspire-injected connection string key ("app") and fall back to DefaultConnection, then localhost
var connString = builder.Configuration.GetConnectionString("app")
                 ?? builder.Configuration.GetConnectionString("DefaultConnection")
                 ?? "Host=localhost;Port=5432;Database=app;Username=postgres;Password=postgres";

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connString));

// Movies service for server-side prerendering
builder.Services.AddScoped<IMoviesApi, MoviesServerService>();

var app = builder.Build();

// This middleware is crucial for logging request details.
app.UseSerilogRequestLogging();

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
