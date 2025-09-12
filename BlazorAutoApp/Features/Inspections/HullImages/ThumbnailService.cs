using SixLabors.ImageSharp;
using SixLabors.ImageSharp.Formats.Jpeg;
using SixLabors.ImageSharp.Processing;
using SixLabors.ImageSharp.PixelFormats;

namespace BlazorAutoApp.Features.Inspections.HullImages;

public interface IThumbnailService
{
    Task<string> GetOrCreateThumbnailAsync(string storageKey, int maxSize, CancellationToken ct = default);
}

public class ThumbnailService(IWebHostEnvironment env, IOptions<HullImagesStorageOptions> opts) : IThumbnailService
{
    private readonly string _root = Path.IsPathRooted(opts.Value.RootPath)
        ? opts.Value.RootPath
        : Path.Combine(env.ContentRootPath, opts.Value.RootPath);

    public async Task<string> GetOrCreateThumbnailAsync(string storageKey, int maxSize, CancellationToken ct = default)
    {
        if (maxSize <= 0) maxSize = 256;
        // Place under thumbs/{size}/{storageKey without extension}.jpg
        var inputPath = Path.Combine(_root, storageKey.Replace('/', Path.DirectorySeparatorChar));
        var dirOfKey = Path.GetDirectoryName(storageKey)?.Replace('/', Path.DirectorySeparatorChar) ?? string.Empty;
        var fileNameNoExt = Path.GetFileNameWithoutExtension(storageKey);
        var thumbDir = Path.Combine(_root, "thumbs", maxSize.ToString(), dirOfKey);
        Directory.CreateDirectory(thumbDir);
        var thumbRel = Path.Combine("thumbs", maxSize.ToString(), dirOfKey, fileNameNoExt + ".jpg").Replace('\\', '/');
        var thumbPath = Path.Combine(_root, thumbRel.Replace('/', Path.DirectorySeparatorChar));

        if (!File.Exists(thumbPath))
        {
            try
            {
                using var image = await Image.LoadAsync(inputPath, ct);
                var w = image.Width; var h = image.Height;
                var scale = Math.Min((double)maxSize / w, (double)maxSize / h);
                if (scale > 1.0) scale = 1.0; // Do not upscale
                var newW = Math.Max(1, (int)Math.Round(w * scale));
                var newH = Math.Max(1, (int)Math.Round(h * scale));
                image.Mutate(ctx => ctx.Resize(newW, newH));
                var encoder = new JpegEncoder { Quality = 80 };
                await image.SaveAsJpegAsync(thumbPath, encoder, ct);
            }
            catch
            {
                // Fallback: create a small placeholder JPEG if source is corrupt/unsupported
                var w = Math.Max(1, Math.Min(maxSize, 8));
                var h = Math.Max(1, Math.Min(maxSize, 8));
                using var placeholder = new Image<Rgba32>(w, h);
                var gray = new Rgba32(0xD3, 0xD3, 0xD3); // light gray
                placeholder.ProcessPixelRows(accessor =>
                {
                    for (int y = 0; y < accessor.Height; y++)
                    {
                        var row = accessor.GetRowSpan(y);
                        row.Fill(gray);
                    }
                });
                var encoder = new JpegEncoder { Quality = 60 };
                await placeholder.SaveAsJpegAsync(thumbPath, encoder, ct);
            }
        }

        return thumbRel;
    }
}
