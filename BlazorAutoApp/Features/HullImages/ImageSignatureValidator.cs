namespace BlazorAutoApp.Features.HullImages;

public static class ImageSignatureValidator
{
    // Checks common image magic numbers: JPEG, PNG, GIF, WEBP, BMP
    public static bool IsSupportedImage(Stream stream)
    {
        if (!stream.CanRead) return false;
        var max = 12;
        var buffer = new byte[max];
        var read = stream.Read(buffer, 0, buffer.Length);
        stream.Seek(0, SeekOrigin.Begin);
        if (read < 3) return false;

        // JPEG: FF D8 FF
        if (read >= 3 && buffer[0] == 0xFF && buffer[1] == 0xD8 && buffer[2] == 0xFF)
            return true;

        // PNG: 89 50 4E 47 0D 0A 1A 0A
        if (read >= 8 && buffer[0] == 0x89 && buffer[1] == 0x50 && buffer[2] == 0x4E && buffer[3] == 0x47 &&
            buffer[4] == 0x0D && buffer[5] == 0x0A && buffer[6] == 0x1A && buffer[7] == 0x0A)
            return true;

        // GIF: GIF87a or GIF89a
        if (read >= 6 && buffer[0] == (byte)'G' && buffer[1] == (byte)'I' && buffer[2] == (byte)'F' &&
            buffer[3] == (byte)'8' && (buffer[4] == (byte)'7' || buffer[4] == (byte)'9') && buffer[5] == (byte)'a')
            return true;

        // WEBP: RIFF .... WEBP
        if (read >= 12 && buffer[0] == (byte)'R' && buffer[1] == (byte)'I' && buffer[2] == (byte)'F' && buffer[3] == (byte)'F' &&
            buffer[8] == (byte)'W' && buffer[9] == (byte)'E' && buffer[10] == (byte)'B' && buffer[11] == (byte)'P')
            return true;

        // BMP: BM
        if (read >= 2 && buffer[0] == (byte)'B' && buffer[1] == (byte)'M')
            return true;

        return false;
    }
}

