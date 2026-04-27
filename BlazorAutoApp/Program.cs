using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;
using InspectionRecord = BlazorAutoApp.Core.Features.Inspections.Inspection.Inspection;
using InspectionFlowRecord = BlazorAutoApp.Core.Features.Inspections.InspectionFlow.InspectionFlow;
using VesselRecord = BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Vessel;
using ClientImports = BlazorAutoApp.Client._Imports;
using BlazorAutoApp.Features.IdentityShowcase;
using BlazorAutoApp.Features.Inspections.HullImages;
using BlazorAutoApp.Features.Inspections.InspectionFlow;
using BlazorAutoApp.Features.Inspections.VesselPartDetails;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using System.Security.Cryptography.X509Certificates;

var builder = WebApplication.CreateBuilder(args);

// Central defaults + standard config + environment variables (no prefix)
builder.Configuration
    .AddJsonFile("settings.defaults.json", optional: false, reloadOnChange: true)
    .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
    .AddJsonFile($"appsettings.{builder.Environment.EnvironmentName}.json", optional: true, reloadOnChange: true)
    .AddEnvironmentVariables();

//
string GetEnvVar(string key)
{
    var val = Environment.GetEnvironmentVariable(key);
    if (string.IsNullOrWhiteSpace(val))
    {
        throw new InvalidOperationException($"Missing environment variable: {key}");
    }
    return val;
}


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
var dataProtectionBuilder = builder.Services.AddDataProtection()
    .SetApplicationName("BlazorAutoApp")
    .PersistKeysToFileSystem(new DirectoryInfo(dpKeysPath));
if (builder.Environment.IsEnvironment("Docker"))
{
    var certPath = Environment.GetEnvironmentVariable("ASPNETCORE_Kestrel__Certificates__Default__Path");
    var certPassword = Environment.GetEnvironmentVariable("ASPNETCORE_Kestrel__Certificates__Default__Password");
    if (!string.IsNullOrWhiteSpace(certPath) && File.Exists(certPath))
    {
        try
        {
            dataProtectionBuilder.ProtectKeysWithCertificate(
                X509CertificateLoader.LoadPkcs12FromFile(certPath, certPassword));
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[Startup] Failed to configure DataProtection certificate encryption: {ex.Message}");
        }
    }
}
else if (OperatingSystem.IsWindows())
{
    dataProtectionBuilder.ProtectKeysWithDpapi();
}

builder.Services.AddAntiforgery(options =>
{
    // Avoid cross-environment stale-token decrypt errors (local vs docker key rings).
    options.Cookie.Name = builder.Environment.IsEnvironment("Docker")
        ? "BlazorAutoApp.Antiforgery.Docker"
        : "BlazorAutoApp.Antiforgery";
});

// EF Core with PostgreSQL: prefer ConnectionStrings:DefaultConnection; fallback to Database__* env vars.
var explicitConn = builder.Configuration.GetConnectionString("DefaultConnection");
var connString = !string.IsNullOrWhiteSpace(explicitConn)
    ? explicitConn
    : $"Host={GetEnvVar("Database__Host")};Port={GetEnvVar("Database__Port")};Database={GetEnvVar("Database__Name")};Username={GetEnvVar("Database__Username")};Password={GetEnvVar("Database__Password")}";

void ConfigureDbContext(DbContextOptionsBuilder options)
{
    options.UseNpgsql(connString);
    // Identity + IDbContextFactory can produce runtime-only model diffs; do not crash startup on that warning.
    options.ConfigureWarnings(warnings => warnings.Ignore(RelationalEventId.PendingModelChangesWarning));
}

builder.Services.AddDbContext<AppDbContext>(ConfigureDbContext, optionsLifetime: ServiceLifetime.Singleton);
builder.Services.AddDbContextFactory<AppDbContext>(ConfigureDbContext);
builder.Services.AddRazorPages();

builder.Services
    .AddMoviesFeature(builder.Configuration)
    .AddHullImagesFeature(builder.Configuration)
    .AddInspectionFlowFeature()
    .AddVesselPartDetailsFeature()
    .AddIdentityShowcaseFeature();

// Redis (distributed cache) + Hybrid cache
var redisConn = builder.Configuration.GetSection("Redis").GetValue<string>("Configuration");
if (!string.IsNullOrWhiteSpace(redisConn) && !string.Equals(redisConn, "CHANGE_ME", StringComparison.OrdinalIgnoreCase))
{
    builder.Services.AddStackExchangeRedisCache(options => { options.Configuration = redisConn; });
}
else
{
    // Fallback to in-memory distributed cache when Redis not configured
    builder.Services.AddDistributedMemoryCache();
}
builder.Services.AddHybridCache();


builder.Services
    .AddDefaultIdentity<ApplicationUser>(options =>
    {
        options.SignIn.RequireConfirmedAccount = false;
    })
    .AddRoles<IdentityRole>()
    .AddEntityFrameworkStores<AppDbContext>();

var googleClientId = builder.Configuration["Authentication:Google:ClientId"];
var googleClientSecret = builder.Configuration["Authentication:Google:ClientSecret"];
if (!string.IsNullOrWhiteSpace(googleClientId) && !string.IsNullOrWhiteSpace(googleClientSecret))
{
    builder.Services
        .AddAuthentication()
        .AddGoogle(options =>
        {
            options.ClientId = googleClientId;
            options.ClientSecret = googleClientSecret;
        });
}

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

app.UseAuthentication();
app.UseAuthorization();

app.UseAntiforgery();

// This app does not need browser local-network access permissions.
// Explicitly opt out to avoid browser permission prompts related to local network access.
app.Use(async (ctx, next) =>
{
    ctx.Response.Headers["Permissions-Policy"] = "local-network-access=()";
    await next();
});

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

        if (app.Environment.IsDevelopment())
        {
            var roleManager = sp.GetRequiredService<RoleManager<IdentityRole>>();
            await EnsureRoleExistsAsync(roleManager, logger, "Admin");
            await EnsureRoleExistsAsync(roleManager, logger, "Viewer");
        }

        // Seed demo inspection and vessel list
        try
        {
            // Seed a fixed Inspection for Admin demo flow
            var adminFlowId = Guid.Parse("11111111-1111-1111-1111-111111111111");
            var existingAdmin = await db.Inspections.FirstOrDefaultAsync(i => i.Id == adminFlowId);
            if (existingAdmin is null)
            {
                db.Inspections.Add(new InspectionRecord
                {
                    Id = adminFlowId,
                    CreatedAtUtc = DateTime.UtcNow.AddDays(-1)
                });
                // Optional: seed an initial flow record
                db.InspectionFlows.Add(new InspectionFlowRecord
                {
                    Id = adminFlowId,
                    VesselName = null,
                    InspectionType = InspectionType.GoProInspection
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
                    var vessels = lines.Select(name => new VesselRecord { Name = name }).ToList();
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
            logger.LogWarning(seedEx, "Inspection/Vessel seed step skipped due to error");
        }
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "EF migrations failed at startup");
        throw;
    }
}

app.MapStaticAssets();
app.UseHullImagesTus();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode()
    .AddInteractiveWebAssemblyRenderMode()
    .AddAdditionalAssemblies(typeof(ClientImports).Assembly);
app.MapRazorPages();

// Minimal API endpoints
app.MapMoviesFeature();
app.MapHullImagesFeature();
app.MapInspectionFlowFeature();
app.MapVesselPartDetailsFeature();
app.MapIdentityShowcaseFeature();

async Task EnsureRoleExistsAsync(RoleManager<IdentityRole> roleManager, ILogger<Program> logger, string roleName)
{
    if (await roleManager.RoleExistsAsync(roleName))
    {
        return;
    }

    var result = await roleManager.CreateAsync(new IdentityRole(roleName));
    if (!result.Succeeded)
    {
        var errors = string.Join("; ", result.Errors.Select(e => $"{e.Code}: {e.Description}"));
        throw new InvalidOperationException($"Failed creating role '{roleName}'. {errors}");
    }

    logger.LogInformation("Created identity role {RoleName}", roleName);
}

app.Run();

//A hacky solution to use Testcontainers with WebApplication.CreateBuilder for integration tests
public partial class Program;


