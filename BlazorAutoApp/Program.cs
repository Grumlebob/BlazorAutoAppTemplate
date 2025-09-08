using tusdotnet;
using BlazorAutoApp.Core.Features.HullImages;
using BlazorAutoApp.Features.HullImages;
using tusdotnet.Interfaces;
using tusdotnet.Models;
using tusdotnet.Models.Configuration;
using tusdotnet.Stores;

var builder = WebApplication.CreateBuilder(args);

// Optional: include Docker-specific configuration when running in containers
if (builder.Environment.IsEnvironment("Docker"))
{
    builder.Configuration.AddJsonFile("appsettings.Docker.json", optional: true);
}

// SERILOG CONFIGURATION ---
builder.Host.UseSerilog((ctx, _, config) =>
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
builder.Services.Configure<MoviesCacheOptions>(
    builder.Configuration.GetSection("Cache:Movies"));

// HullImages services
builder.Services.Configure<HullImagesStorageOptions>(builder.Configuration.GetSection("Storage:HullImages"));
builder.Services.AddScoped<IHullImagesApi, HullImagesServerService>();
builder.Services.AddSingleton<IHullImageStore, LocalHullImageStore>();
builder.Services.AddSingleton<IThumbnailService, ThumbnailService>();
builder.Services.AddSingleton<ITusResultRegistry, TusResultRegistryRedis>();

// Redis (distributed cache) + Hybrid cache
var redisConn = builder.Configuration.GetSection("Redis").GetValue<string>("Configuration") ?? "localhost:6379";
builder.Services.AddStackExchangeRedisCache(options => { options.Configuration = redisConn; });
builder.Services.AddHybridCache();

// HttpClient for components (server prerendering + interactive server)

var app = builder.Build();

// Concise per-request logging
app.UseSerilogRequestLogging(options =>
{
    options.MessageTemplate = "HTTP {RequestMethod} {RequestPath} responded {StatusCode} in {Elapsed:0.0000} ms";

    // Adjust log level (e.g., demote health checks)
    options.GetLevel = (http, _, ex) =>
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
        ctx.Set("UserName", http.User.Identity?.Name ?? "");
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
// TUS resumable uploads at /api/hull-images/tus
app.UseTus(context =>
{
    var env = context.RequestServices.GetRequiredService<IHostEnvironment>();
    var contentRoot = env.ContentRootPath;
    var tusRoot = Path.Combine(contentRoot, "Storage", "Tus");
    Directory.CreateDirectory(tusRoot);

    var cfg = new DefaultTusConfiguration
    {
        UrlPath = "/api/hull-images/tus",
        Store = new TusDiskStore(tusRoot),
        MaxAllowedUploadSizeInBytesLong = 1_073_741_824L,
        Events = new Events
        {
            OnBeforeCreateAsync = async ctx =>
            {
                // Enforce required metadata
                var meta = ctx.Metadata ?? new Dictionary<string, tusdotnet.Models.Metadata>();
                if (!meta.ContainsKey("filename"))
                {
                    ctx.FailRequest("Missing 'filename' metadata.");
                    return;
                }
                // Optional contentType
                await Task.CompletedTask;
            },
            OnFileCompleteAsync = async ctx =>
            {
                var http = ctx.HttpContext;
                var sp = http.RequestServices;
                var store = sp.GetRequiredService<IHullImageStore>();
                var api = sp.GetRequiredService<IHullImagesApi>();
                var logger = sp.GetRequiredService<ILogger<Program>>();

                var file = await ctx.GetFileAsync();
                var meta = await file.GetMetadataAsync(http.RequestAborted);
                meta.TryGetValue("filename", out var fnameMeta);
                meta.TryGetValue("contentType", out var ctypeMeta);
                meta.TryGetValue("correlationId", out var correlationMeta);
                var fileName = fnameMeta?.GetString(System.Text.Encoding.UTF8) ?? "upload.bin";
                var contentType = ctypeMeta?.GetString(System.Text.Encoding.UTF8);

                await using var src = await file.GetContentAsync(http.RequestAborted);
                var stored = await store.SaveAsync(src, fileName, contentType, http.RequestAborted);

                int? width = null, height = null;
                try
                {
                    await using var verify = await store.OpenReadAsync(stored.StorageKey, http.RequestAborted);
                    using var img = SixLabors.ImageSharp.Image.Load(verify);
                    width = img.Width; height = img.Height;
                }
                catch
                {
                    await store.DeleteAsync(stored.StorageKey, http.RequestAborted);
                    logger.LogWarning("TUS upload rejected (not decodable image): {File}", fileName);
                    return;
                }

                var created = await api.CreateAsync(new CreateHullImageRequest
                {
                    OriginalFileName = fileName,
                    ContentType = contentType,
                    ByteSize = stored.ByteSize,
                    StorageKey = stored.StorageKey,
                    Sha256 = stored.Sha256,
                    Width = width,
                    Height = height
                });
                logger.LogInformation("TUS upload completed -> HullImage {Id}", created.Id);

                // If client provided correlationId, record the mapping for lookup
                if (correlationMeta is not null)
                {
                    try
                    {
                        var s = correlationMeta.GetString(System.Text.Encoding.UTF8);
                        if (Guid.TryParse(s, out var corr))
                        {
                            var reg = sp.GetRequiredService<ITusResultRegistry>();
                            reg.Set(corr, created.Id);
                        }
                    }
                    catch { /* ignore correlation issues */ }
                }

                // Clean up the TUS file after completion
                // Attempt to delete TUS temp file if termination is supported
                if (ctx.Store is ITusTerminationStore term)
                {
                    try { await term.DeleteFileAsync(ctx.FileId, http.RequestAborted); } catch { }
                }
            }
        }
    };
    return cfg;
});
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode()
    .AddInteractiveWebAssemblyRenderMode()
    .AddAdditionalAssemblies(typeof(BlazorAutoApp.Client._Imports).Assembly);

// Minimal API endpoints
app.MapMovieEndpoints();
app.MapHullImageEndpoints();

app.Run();

//A hacky solution to use Testcontainers with WebApplication.CreateBuilder for integration tests
public partial class Program;
