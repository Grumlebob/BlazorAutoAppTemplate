using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.HullImages;
using BlazorAutoApp.Test.TestingSetup;
using Xunit;

namespace BlazorAutoApp.Test.Features.HullImages;

[Collection("MediaTestCollection")]
public class ChunkedUploadTests : IAsyncLifetime
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;

    public ChunkedUploadTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
    }

    private record InitiateUploadResponse(Guid UploadSessionId, int ChunkSizeBytes);

    [Fact]
    public async Task Chunked_Upload_And_Download_Matches()
    {
        var initReq = new HttpRequestMessage(HttpMethod.Post, "/api/hull-images/uploads");
        initReq.Headers.Add("X-File-Name", "chunked.bin");
        initReq.Headers.Add("X-Content-Type", "application/octet-stream");
        var initRes = await _client.SendAsync(initReq);
        Assert.Equal(HttpStatusCode.OK, initRes.StatusCode);
        var init = await initRes.Content.ReadFromJsonAsync<InitiateUploadResponse>(new JsonSerializerOptions(JsonSerializerDefaults.Web));
        Assert.NotNull(init);

        // Build 3 chunks with leading JPEG magic in the first chunk to pass server validation
        var sizes = new[] { 1024, 4096, 2048 };
        var chunks = sizes.Select(n => new byte[n]).ToArray();
        chunks[0][0] = 0xFF; chunks[0][1] = 0xD8; chunks[0][2] = 0xFF; chunks[0][3] = 0xE0;
        for (int i = 0; i < chunks.Length; i++)
            for (int j = (i == 0 ? 4 : 0); j < chunks[i].Length; j++)
                chunks[i][j] = (byte)((i * 37 + j) % 251);

        for (var i = 0; i < chunks.Length; i++)
        {
            using var chunkContent = new ByteArrayContent(chunks[i]);
            var put = await _client.PutAsync($"/api/hull-images/uploads/{init!.UploadSessionId}/chunks/{i}", chunkContent);
            Assert.True(put.StatusCode is HttpStatusCode.Accepted or HttpStatusCode.OK);
        }

        var complete = await _client.PostAsync($"/api/hull-images/uploads/{init!.UploadSessionId}/complete", content: null);
        Assert.Equal(HttpStatusCode.OK, complete.StatusCode);
        var created = await complete.Content.ReadFromJsonAsync<CreateHullImageResponse>();
        Assert.NotNull(created);

        var all = chunks.SelectMany(b => b).ToArray();
        var bytes = await _client.GetByteArrayAsync($"/api/hull-images/{created!.Id}/original");
        Assert.Equal(all.Length, bytes.Length);
        Assert.Equal(all, bytes);
    }

    public Task InitializeAsync() => Task.CompletedTask;
    public Task DisposeAsync() => _resetDatabase();
}
