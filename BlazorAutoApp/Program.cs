using BlazorAutoApp.Core.Features.Email;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;
using tusdotnet;
using BlazorAutoApp.Features.Email;
using BlazorAutoApp.Features.Inspections.StartHullInspectionEmail;
using BlazorAutoApp.Features.Inspections.VerifyInspectionEmail;
using BlazorAutoApp.Features.Inspections.InspectionFlow;
using Microsoft.AspNetCore.DataProtection;
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

// Persist Data Protection keys to a shared folder so antiforgery/state survives container restarts
var dpKeysPath = Path.Combine(builder.Environment.ContentRootPath, "Storage", "DataProtection-Keys");
Directory.CreateDirectory(dpKeysPath);
builder.Services.AddDataProtection()
    .SetApplicationName("BlazorAutoApp")
    .PersistKeysToFileSystem(new DirectoryInfo(dpKeysPath));

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
// Email services
builder.Services.AddScoped<IEmailApi, EmailServerService>();
// Inspections subfeatures
builder.Services.AddScoped<IStartHullInspectionEmailApi, StartHullInspectionEmailServerService>();
builder.Services.AddScoped<IInspectionApi, InspectionServerService>();
builder.Services.AddScoped<IInspectionFlowApi, InspectionFlowServerService>();
// Note: Do NOT register HttpClient in server (architecture rule)

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

// Apply EF Core migrations at startup (and log)
using (var scope = app.Services.CreateScope())
{
    var sp = scope.ServiceProvider;
    var db = sp.GetRequiredService<AppDbContext>();
    var logger = sp.GetRequiredService<ILogger<Program>>();
    try
    {
        var pending = db.Database.GetPendingMigrations().ToList();
        if (pending.Count > 0)
        {
            logger.LogInformation("Applying {Count} EF migrations: {Migrations}", pending.Count, string.Join(", ", pending));
        }
        else
        {
            logger.LogInformation("No EF migrations pending");
        }
        db.Database.Migrate();
        // Seed 20 dummy companies if table empty
        try
        {
            if (!await db.CompanyDetails.AnyAsync())
            {
                var companies = Enumerable.Range(1, 20)
                    .Select(i => new CompanyDetail
                    {
                        Name = $"TestCompany{i}",
                        Email = $"testcompany{i}@example.com",
                        HasActivatedLatestInspectionEmail = true
                    }).ToList();
                companies.Add(new CompanyDetail
                {
                    Name = "Jacob Grum",
                    Email = "jgrum@live.dk",
                    HasActivatedLatestInspectionEmail = true
                });
                db.CompanyDetails.AddRange(companies);
                await db.SaveChangesAsync();
                logger.LogInformation("Seeded {Count} CompanyDetails items", companies.Count);
            }
            else
            {
                logger.LogInformation("CompanyDetails already seeded");
            }

            // Seed a fixed, verified Inspection for Admin demo flow
            var adminFlowId = Guid.Parse("11111111-1111-1111-1111-111111111111");
            var existingAdmin = await db.Inspections.FirstOrDefaultAsync(i => i.Id == adminFlowId);
            if (existingAdmin is null)
            {
                // Ensure a company exists to associate with
                var companyId = await db.CompanyDetails.Select(c => c.Id).OrderBy(x => x).FirstAsync();
                db.Inspections.Add(new BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection
                {
                    Id = adminFlowId,
                    CompanyId = companyId,
                    PasswordSalt = "seed",
                    PasswordHash = "seed",
                    CreatedAtUtc = DateTime.UtcNow.AddDays(-1),
                    VerifiedAtUtc = DateTime.UtcNow
                });
                // Optional: seed an initial flow record
                db.InspectionFlows.Add(new BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow
                {
                    Id = adminFlowId,
                    CompanyId = companyId,
                    VesselName = null,
                    InspectionType = BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionType.GoProInspection
                });
                await db.SaveChangesAsync();
                logger.LogInformation("Seeded Admin demo inspection flow with Id {Id}", adminFlowId);
            }

            // Seed Vessels from shipNames.txt (reset to file content every startup)
            try
            {
                var root = builder.Environment.ContentRootPath;
                var namesPath = Path.Combine(root, "shipNames.txt");
                if (File.Exists(namesPath))
                {
                    var lines = (await File.ReadAllLinesAsync(namesPath))
                        .Select(s => s.Trim())
                        .Where(s => !string.IsNullOrEmpty(s))
                        .Distinct(StringComparer.Ordinal)
                        .OrderBy(s => s)
                        .ToList();

                    // Clear existing and insert fresh
                    await db.Vessels.ExecuteDeleteAsync();
                    var vessels = lines.Select(name => new BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Vessel { Name = name }).ToList();
                    db.Vessels.AddRange(vessels);
                    await db.SaveChangesAsync();
                    logger.LogInformation("Seeded {Count} vessels from shipNames.txt (reset)", vessels.Count);
                }
                else
                {
                    logger.LogWarning("shipNames.txt not found; Vessels table not seeded");
                }
            }
            catch (Exception vex)
            {
                logger.LogWarning(vex, "Failed to seed Vessels from shipNames.txt");
            }
        }
        catch (Exception seedEx)
        {
            logger.LogWarning(seedEx, "CompanyDetails seed step skipped due to error");
        }
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "EF migrations failed at startup");
        throw;
    }
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
        MaxAllowedUploadSizeInBytesLong = 10_737_418_240L,
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
                    var info = SixLabors.ImageSharp.Image.Identify(verify);
                    if (info is null)
                        throw new InvalidOperationException("Unrecognized image format");
                    width = info.Width; height = info.Height;
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
app.MapEmailEndpoints();
app.MapStartHullInspectionEmailEndpoints();
app.MapInspectionEndpoints();
app.MapInspectionFlowEndpoints();

app.Run();

//A hacky solution to use Testcontainers with WebApplication.CreateBuilder for integration tests
public partial class Program;
