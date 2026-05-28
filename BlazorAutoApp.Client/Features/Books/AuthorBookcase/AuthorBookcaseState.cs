using BlazorAutoApp.Client.Features.Books.Shared;
using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;
using Microsoft.Extensions.Logging;

namespace BlazorAutoApp.Client.Features.Books.AuthorBookcase;

public sealed class AuthorBookcaseState(
    IAuthorBooksApi authorBooks,
    ILogger<AuthorBookcaseState> logger)
{
    private readonly IAuthorBooksApi _authorBooks = authorBooks;
    private readonly ILogger<AuthorBookcaseState> _logger = logger;
    private int _version;

    public event Action? Changed;

    public bool IsLoading { get; private set; } = true;

    public string? Error { get; private set; }

    public IReadOnlyList<AuthorBookListItemResponse> Books { get; private set; } = [];

    public IReadOnlyList<BookcaseBook> ShelfBooks { get; private set; } = [];

    public void ApplyLoadedBooks(IReadOnlyList<AuthorBookListItemResponse> books)
    {
        Interlocked.Increment(ref _version);
        ApplyBooks(books.OrderBy(book => book.Id).ToList());
        Error = null;
        IsLoading = false;
        NotifyChanged();
    }

    public async Task LoadAsync(CancellationToken cancellationToken = default)
    {
        var version = Interlocked.Increment(ref _version);
        IsLoading = true;
        Error = null;
        NotifyChanged();

        try
        {
            var response = await _authorBooks.GetAsync(cancellationToken);
            if (version != Volatile.Read(ref _version))
            {
                return;
            }

            ApplyLoadedBooks(response.Books);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception ex)
        {
            if (version != Volatile.Read(ref _version))
            {
                return;
            }

            _logger.LogWarning(ex, "Author bookcase load failed.");
            Error = "The authors bookcase could not be loaded.";
            IsLoading = false;
            NotifyChanged();
        }
    }

    private void ApplyBooks(IReadOnlyList<AuthorBookListItemResponse> books)
    {
        Books = books;
        ShelfBooks = books
            .Select(book => new BookcaseBook(
                book.Id,
                book.Title,
                book.Url,
                $"/books?authorBookId={book.Id.ToString(System.Globalization.CultureInfo.InvariantCulture)}&bookMode=view"))
            .ToList();
    }

    private void NotifyChanged() => Changed?.Invoke();
}
