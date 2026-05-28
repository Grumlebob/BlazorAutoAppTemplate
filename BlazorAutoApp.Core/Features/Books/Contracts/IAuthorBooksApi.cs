using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;

namespace BlazorAutoApp.Core.Features.Books.Contracts;

public interface IAuthorBooksApi
{
    Task<GetAuthorBooksResponse> GetAsync(CancellationToken cancellationToken = default);

    Task<GetAuthorBookResponse?> GetByIdAsync(GetAuthorBookRequest req, CancellationToken cancellationToken = default);
}
