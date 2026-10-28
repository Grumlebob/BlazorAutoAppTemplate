using System.Net;
using GrumPlates.Core.Features.Books.Contracts;
using GrumPlates.Core.Features.Books.UseCases.CreateBook;
using GrumPlates.Core.Features.Books.UseCases.DeleteBook;
using GrumPlates.Core.Features.Books.UseCases.GetBook;
using GrumPlates.Core.Features.Books.UseCases.GetBooks;
using GrumPlates.Core.Features.Books.UseCases.UpdateBook;

namespace GrumPlates.Client.Features.Books;

public class BooksClientService(HttpClient http) : IBooksApi
{
    private readonly HttpClient _http = http;

    public async Task<GetBooksResponse> GetAsync(CancellationToken cancellationToken = default)
    {
        var res = await _http.GetFromJsonAsync<GetBooksResponse>("api/books", cancellationToken);
        return res ?? new GetBooksResponse { Books = [] };
    }

    public async Task<GetBookResponse?> GetByIdAsync(GetBookRequest req, CancellationToken cancellationToken = default)
    {
        using var res = await _http.GetAsync($"api/books/{req.Id}", cancellationToken);
        if (res.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }

        res.EnsureSuccessStatusCode();
        return await res.Content.ReadFromJsonAsync<GetBookResponse>(cancellationToken);
    }

    public async Task<CreateBookResponse> CreateAsync(CreateBookRequest req, CancellationToken cancellationToken = default)
    {
        using var res = await _http.PostAsJsonAsync("api/books", req, cancellationToken);
        res.EnsureSuccessStatusCode();
        return (await res.Content.ReadFromJsonAsync<CreateBookResponse>(cancellationToken))!;
    }

    public async Task<bool> UpdateAsync(UpdateBookRequest req, CancellationToken cancellationToken = default)
    {
        using var res = await _http.PutAsJsonAsync($"api/books/{req.Id}", req, cancellationToken);
        if (res.StatusCode == HttpStatusCode.NoContent) return true;
        if (res.StatusCode == HttpStatusCode.NotFound) return false;
        res.EnsureSuccessStatusCode();
        return true;
    }

    public async Task<bool> DeleteAsync(DeleteBookRequest req, CancellationToken cancellationToken = default)
    {
        using var res = await _http.DeleteAsync($"api/books/{req.Id}", cancellationToken);
        if (res.StatusCode == HttpStatusCode.NoContent) return true;
        if (res.StatusCode == HttpStatusCode.NotFound) return false;
        res.EnsureSuccessStatusCode();
        return true;
    }
}
