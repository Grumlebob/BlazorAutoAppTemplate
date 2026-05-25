using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.DeleteBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;

namespace BlazorAutoApp.Core.Features.Books.Contracts;

public interface IBooksApi
{
    Task<GetBooksResponse> GetAsync(GetBooksRequest req, CancellationToken cancellationToken = default);
    Task<GetBookResponse?> GetByIdAsync(GetBookRequest req, CancellationToken cancellationToken = default);
    Task<CreateBookResponse> CreateAsync(CreateBookRequest req, CancellationToken cancellationToken = default);
    Task<bool> UpdateAsync(UpdateBookRequest req, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(DeleteBookRequest req, CancellationToken cancellationToken = default);
}
