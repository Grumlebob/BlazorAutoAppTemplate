using GrumPlates.Core.Features.Books.UseCases.CreateBook;
using GrumPlates.Core.Features.Books.UseCases.DeleteBook;
using GrumPlates.Core.Features.Books.UseCases.GetBook;
using GrumPlates.Core.Features.Books.UseCases.GetBooks;
using GrumPlates.Core.Features.Books.UseCases.UpdateBook;

namespace GrumPlates.Core.Features.Books.Contracts;

public interface IBooksApi
{
    Task<GetBooksResponse> GetAsync(CancellationToken cancellationToken = default);
    Task<GetBookResponse?> GetByIdAsync(GetBookRequest req, CancellationToken cancellationToken = default);
    Task<CreateBookResponse> CreateAsync(CreateBookRequest req, CancellationToken cancellationToken = default);
    Task<bool> UpdateAsync(UpdateBookRequest req, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(DeleteBookRequest req, CancellationToken cancellationToken = default);
}
