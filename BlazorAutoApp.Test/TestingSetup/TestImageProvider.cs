using System;
using System.IO;
using SixLabors.ImageSharp;

namespace BlazorAutoApp.Test.TestingSetup;

public static class TestImageProvider
{
    private static readonly string RelativePath = Path.Combine("TestingSetup", "Assets", "test-image.PNG");

    // No fallback: tests must include a decodable PNG at the path above.

    public static byte[] GetBytes()
    {
        // Load the provided file (copied to output)
        var candidate = Path.Combine(AppContext.BaseDirectory, RelativePath);
        if (!File.Exists(candidate))
            throw new FileNotFoundException($"Test image not found at '{candidate}'. Add TestingSetup/Assets/test-image.PNG to the test project.");
        var bytes = File.ReadAllBytes(candidate);
        if (!IsDecodablePng(bytes))
            throw new InvalidDataException("Testing image is not a decodable PNG. Replace test-image.PNG with a valid PNG.");
        return bytes;
    }

    private static bool IsDecodablePng(byte[] data)
    {
        try
        {
            using var ms = new MemoryStream(data, writable: false);
            using var img = Image.Load(ms);
            return img.Width > 0 && img.Height > 0;
        }
        catch
        {
            return false;
        }
    }
}
