using System.Net;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;

namespace BlazorAutoApp.Client.Features.Books.AuthorBookcase;

public sealed class AuthorBooksClientService(HttpClient http) : IAuthorBooksApi
{
    private readonly HttpClient _http = http;

    public async Task<GetAuthorBooksResponse> GetAsync(CancellationToken cancellationToken = default)
    {
        var response = await _http.GetFromJsonAsync<GetAuthorBooksResponse>("api/author-books", cancellationToken);
        return response ?? new GetAuthorBooksResponse { Books = [] };
    }

    public async Task<GetAuthorBookResponse?> GetByIdAsync(GetAuthorBookRequest req, CancellationToken cancellationToken = default)
    {
        using var response = await _http.GetAsync($"api/author-books/{req.Id}", cancellationToken);
        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }

        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<GetAuthorBookResponse>(cancellationToken);
    }
}
