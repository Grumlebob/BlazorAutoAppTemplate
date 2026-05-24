using ClientImports = BlazorAutoApp.Client._Imports;
using BlazorAutoApp.Features.IdentityShowcase;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Npgsql;
using StackExchange.Redis;
using System.Security.Cryptography.X509Certificates;

var builder = WebApplication.CreateBuilder(args);

// Central defaults + standard config + environment variables (no prefix)
builder.Configuration
    .AddJsonFile("settings.defaults.json", optional: false, reloadOnChange: true)
    .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
    .AddJsonFile($"appsettings.{builder.Environment.EnvironmentName}.json", optional: true, reloadOnChange: true);

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

// Environment variables must be last so deployment-provided values override Docker defaults.
builder.Configuration.AddEnvironmentVariables();

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

// Redis (distributed cache) + Hybrid cache
var redisConn = builder.Configuration.GetSection("Redis").GetValue<string>("Configuration");
var hasRedis = !string.IsNullOrWhiteSpace(redisConn) &&
               !string.Equals(redisConn, "CHANGE_ME", StringComparison.OrdinalIgnoreCase);
IConnectionMultiplexer? redisMultiplexer = null;
if (hasRedis)
{
    redisMultiplexer = ConnectionMultiplexer.Connect(redisConn!);
    builder.Services.AddSingleton(redisMultiplexer);
}

var dataProtectionBuilder = builder.Services.AddDataProtection()
    .SetApplicationName("BlazorAutoApp");
if (redisMultiplexer is not null)
{
    dataProtectionBuilder.PersistKeysToStackExchangeRedis(redisMultiplexer, "DataProtection-Keys");
}
else
{
    // Local fallback when Redis is not configured.
    var dpKeysPath = Path.Combine(builder.Environment.ContentRootPath, "Storage", "DataProtection-Keys");
    Directory.CreateDirectory(dpKeysPath);
    dataProtectionBuilder.PersistKeysToFileSystem(new DirectoryInfo(dpKeysPath));
}
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

builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders =
        ForwardedHeaders.XForwardedFor |
        ForwardedHeaders.XForwardedProto |
        ForwardedHeaders.XForwardedHost;
    options.KnownIPNetworks.Clear();
    options.KnownProxies.Clear();
});

// EF Core with PostgreSQL: prefer ConnectionStrings:DefaultConnection; fallback to Database__* env vars.
var explicitConn = builder.Configuration.GetConnectionString("DefaultConnection");
var connString = ConfigurePostgresConnectionString(!string.IsNullOrWhiteSpace(explicitConn)
    ? explicitConn
    : $"Host={GetEnvVar("Database__Host")};Port={GetEnvVar("Database__Port")};Database={GetEnvVar("Database__Name")};Username={GetEnvVar("Database__Username")};Password={GetEnvVar("Database__Password")}");

string ConfigurePostgresConnectionString(string connectionString)
{
    var connectionBuilder = new NpgsqlConnectionStringBuilder(connectionString);
    if (!connectionBuilder.ContainsKey("GSS Encryption Mode"))
    {
        connectionBuilder.GssEncryptionMode = GssEncryptionMode.Disable;
    }

    return connectionBuilder.ConnectionString;
}

void ConfigureDbContext(DbContextOptionsBuilder options)
{
    options.UseNpgsql(connString);
    // Identity + IDbContextFactory can produce runtime-only model diffs; do not crash startup on that warning.
    options.ConfigureWarnings(warnings => warnings.Ignore(RelationalEventId.PendingModelChangesWarning));
}

builder.Services.AddDbContext<AppDbContext>(ConfigureDbContext, optionsLifetime: ServiceLifetime.Singleton);
builder.Services.AddDbContextFactory<AppDbContext>(ConfigureDbContext);
builder.Services.AddRazorPages();

var healthChecksBuilder = builder.Services.AddHealthChecks()
    .AddCheck("self", () => HealthCheckResult.Healthy(), tags: ["live"]);

builder.Services
    .AddMoviesFeature(builder.Configuration)
    .AddIdentityShowcaseFeature();

if (hasRedis)
{
    builder.Services.AddStackExchangeRedisCache(options => { options.Configuration = redisConn; });
    healthChecksBuilder.AddCheck<RedisHealthCheck>("redis", tags: ["ready"]);
}
else
{
    // Fallback to in-memory distributed cache when Redis not configured
    builder.Services.AddDistributedMemoryCache();
}
healthChecksBuilder.AddCheck<PostgresHealthCheck>("postgres", tags: ["ready"]);
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

app.UseForwardedHeaders();

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

// Apply EF Core migrations at startup in local development, or when explicitly enabled.
var runMigrationsAtStartup = builder.Configuration.GetValue("Database:RunMigrationsAtStartup", app.Environment.IsDevelopment());
if (runMigrationsAtStartup)
{
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
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "EF migrations failed at startup");
            throw;
        }
    }
}

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode()
    .AddInteractiveWebAssemblyRenderMode()
    .AddAdditionalAssemblies(typeof(ClientImports).Assembly);
app.MapRazorPages();
app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("live")
});
app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready")
});
app.MapHealthChecks("/health", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready")
});

// Minimal API endpoints
app.MapMoviesFeature();
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

internal sealed class PostgresHealthCheck(IDbContextFactory<AppDbContext> dbFactory) : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
            return await db.Database.CanConnectAsync(cancellationToken)
                ? HealthCheckResult.Healthy()
                : HealthCheckResult.Unhealthy("PostgreSQL connection failed.");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("PostgreSQL health check failed.", ex);
        }
    }
}

internal sealed class RedisHealthCheck(IConnectionMultiplexer redis) : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            await redis.GetDatabase().PingAsync();
            return redis.IsConnected
                ? HealthCheckResult.Healthy()
                : HealthCheckResult.Unhealthy("Redis is disconnected.");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("Redis health check failed.", ex);
        }
    }
}

