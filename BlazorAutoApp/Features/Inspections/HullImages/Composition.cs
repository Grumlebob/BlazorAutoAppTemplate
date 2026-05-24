using BlazorAutoApp.Core.Features.Inspections.HullImages.Contracts;
using BlazorAutoApp.Core.Features.Inspections.HullImages.UseCases.CreateHullImage;
using BlazorAutoApp.Features.Inspections.HullImages.Endpoints;
using BlazorAutoApp.Features.Inspections.HullImages.Services;
using BlazorAutoApp.Features.Inspections.HullImages.Storage;
using BlazorAutoApp.Features.Inspections.HullImages.Tus;
using tusdotnet;
using tusdotnet.Interfaces;
using tusdotnet.Models;
using tusdotnet.Models.Configuration;
using tusdotnet.Stores;

namespace BlazorAutoApp.Features.Inspections.HullImages;

public static class Composition
{
    public static IServiceCollection AddHullImagesFeature(this IServiceCollection services, IConfiguration config)
    {
        services.Configure<HullImagesStorageOptions>(config.GetSection("Storage:HullImages"));
        services.AddScoped<IHullImagesApi, HullImagesServerService>();
        services.AddSingleton<IHullImageStore, LocalHullImageStore>();
        services.AddSingleton<IThumbnailService, ThumbnailService>();
        services.AddSingleton<ITusResultRegistry, TusResultRegistryRedis>();
        return services;
    }

    public static IApplicationBuilder UseHullImagesTus(this IApplicationBuilder app)
    {
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
                        var meta = ctx.Metadata ?? [];
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
                        var logger = sp.GetRequiredService<ILoggerFactory>().CreateLogger("HullImagesTus");

                        var file = await ctx.GetFileAsync();
                        var meta = await file.GetMetadataAsync(http.RequestAborted);
                        meta.TryGetValue("filename", out var fnameMeta);
                        meta.TryGetValue("contentType", out var ctypeMeta);
                        meta.TryGetValue("correlationId", out var correlationMeta);
                        meta.TryGetValue("vesselPartId", out var vesselPartMeta);
                        var fileName = fnameMeta?.GetString(System.Text.Encoding.UTF8) ?? "upload.bin";
                        var contentType = ctypeMeta?.GetString(System.Text.Encoding.UTF8);

                        await using var src = await file.GetContentAsync(http.RequestAborted);
                        var stored = await store.SaveAsync(src, fileName, contentType, http.RequestAborted);

                        int? width = null;
                        int? height = null;
                        try
                        {
                            await using var verify = await store.OpenReadAsync(stored.StorageKey, http.RequestAborted);
                            var info = SixLabors.ImageSharp.Image.Identify(verify) ?? throw new InvalidOperationException("Unrecognized image format");
                            width = info.Width;
                            height = info.Height;
                        }
                        catch
                        {
                            await store.DeleteAsync(stored.StorageKey, http.RequestAborted);
                            logger.LogWarning("TUS upload rejected (not decodable image): {File}", fileName);
                            return;
                        }

                        int? vesselPartId = null;
                        if (vesselPartMeta is not null)
                        {
                            try
                            {
                                var raw = vesselPartMeta.GetString(System.Text.Encoding.UTF8);
                                if (int.TryParse(raw, out var vp))
                                {
                                    vesselPartId = vp;
                                }
                            }
                            catch
                            {
                                // ignore metadata parsing errors
                            }
                        }

                        var created = await api.CreateAsync(new CreateHullImageRequest
                        {
                            OriginalFileName = fileName,
                            ContentType = contentType,
                            ByteSize = stored.ByteSize,
                            StorageKey = stored.StorageKey,
                            Sha256 = stored.Sha256,
                            Width = width,
                            Height = height,
                            InspectionVesselPartId = vesselPartId
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
                            catch
                            {
                                // ignore correlation issues
                            }
                        }

                        // Clean up the TUS file after completion
                        if (ctx.Store is ITusTerminationStore term)
                        {
                            try
                            {
                                await term.DeleteFileAsync(ctx.FileId, http.RequestAborted);
                            }
                            catch
                            {
                                // ignore temp cleanup failures
                            }
                        }
                    }
                }
            };
            return cfg;
        });

        return app;
    }

    public static IEndpointRouteBuilder MapHullImagesFeature(this IEndpointRouteBuilder routes)
    {
        routes.MapHullImageEndpoints();
        return routes;
    }
}
