using System.Buffers;
using System.Net;
using System.Net.Http.Headers;

namespace BlazorAutoApp.Client.Services.Http;

public sealed class ProgressStreamContent : HttpContent
{
    private readonly Stream _source;
    private readonly int _bufferSize;
    private readonly Action<long> _progress;
    private readonly long? _contentLength;

    public ProgressStreamContent(Stream source, int bufferSize, Action<long> progress, string? contentType = null, long? contentLength = null)
    {
        _source = source ?? throw new ArgumentNullException(nameof(source));
        _bufferSize = bufferSize > 0 ? bufferSize : 81920;
        _progress = progress ?? throw new ArgumentNullException(nameof(progress));
        _contentLength = contentLength;
        if (!string.IsNullOrWhiteSpace(contentType))
        {
            Headers.ContentType = new MediaTypeHeaderValue(contentType);
        }
        if (contentLength.HasValue)
        {
            Headers.ContentLength = contentLength.Value;
        }
    }

    protected override async Task SerializeToStreamAsync(Stream stream, TransportContext? context, CancellationToken cancellationToken)
    {
        var buffer = ArrayPool<byte>.Shared.Rent(_bufferSize);
        try
        {
            long total = 0;
            int read;
            while ((read = await _source.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken)) > 0)
            {
                await stream.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
                total += read;
                _progress(total);
            }
        }
        finally
        {
            ArrayPool<byte>.Shared.Return(buffer);
        }
    }

    protected override Task SerializeToStreamAsync(Stream stream, TransportContext? context)
    {
        return SerializeToStreamAsync(stream, context, CancellationToken.None);
    }

    protected override bool TryComputeLength(out long length)
    {
        if (_contentLength.HasValue)
        {
            length = _contentLength.Value;
            return true;
        }
        length = 0;
        return false;
    }
}
