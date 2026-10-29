using GrumPlates.Client.Features.Books.BookPage;
using GrumPlates.Client.Features.Books.UserBookcase;
using GrumPlates.Core.Features.Books.Contracts;
using GrumPlates.Core.Features.Books.UseCases.CreateBook;
using GrumPlates.Core.Features.Books.UseCases.GetAuthorBook;
using GrumPlates.Core.Features.Books.UseCases.GetBook;
using GrumPlates.Core.Features.Books.UseCases.UpdateBook;
using Microsoft.AspNetCore.Components.Authorization;

namespace GrumPlates.Client.Features.Books.BookModal;

public sealed class BookModalLifecycle(
    IBooksApi books,
    IAuthorBooksApi authorBooks,
    UserBookcaseState userBooks,
    Microsoft.Extensions.Logging.ILogger logger,
    Action<string, bool> navigate) : IDisposable
{
    private readonly IBooksApi _books = books;
    private readonly IAuthorBooksApi _authorBooks = authorBooks;
    private readonly UserBookcaseState _userBooks = userBooks;
    private readonly Microsoft.Extensions.Logging.ILogger _logger = logger;
    private readonly Action<string, bool> _navigate = navigate;
    private int _loadVersion;
    private CancellationTokenSource? _loadCancellation;
    private CancellationTokenSource? _operationCancellation;
    private string? _editorModelRequestKey;
    private string _uri = "";

    public event Action? Changed;

    public BookModalRouteState? Request { get; private set; }
    public BookModalViewModel? ViewModel { get; private set; }
    public BookPageEditorModel EditorModel { get; private set; } = new();
    public bool Loading { get; private set; }
    public bool Saving { get; private set; }
    public bool Deleting { get; private set; }
    public bool ConfirmingDelete { get; private set; }
    public string? Error { get; private set; }
    public string? SaveError { get; private set; }

    public bool CanDelete => Request is { Source: BookModalSource.User, UserBookId: not null };

    public async Task LoadAsync(BookModalRouteState? request, Task<AuthenticationState> authenticationStateTask, string uri)
    {
        var loadCancellation = StartLoad(out var version);
        CancelActiveOperation();
        var cancellationToken = loadCancellation.Token;
        _uri = uri;
        Request = request;
        ViewModel = null;
        Error = null;
        SaveError = null;
        Saving = false;
        Deleting = false;
        ConfirmingDelete = false;

        if (request is null)
        {
            Loading = false;
            _editorModelRequestKey = null;
            NotifyChanged();
            CompleteLoad(loadCancellation);
            return;
        }

        Loading = true;
        NotifyChanged();

        try
        {
            if (request.Mode is BookModalMode.Create or BookModalMode.Edit)
            {
                var authState = await authenticationStateTask;
                if (!IsCurrentLoad(version, cancellationToken))
                {
                    return;
                }

                if (authState.User.Identity?.IsAuthenticated != true)
                {
                    var returnUrl = Uri.EscapeDataString(_uri);
                    _navigate($"Account/Login?returnUrl={returnUrl}", true);
                    return;
                }
            }

            switch (request)
            {
                case { Source: BookModalSource.Author, AuthorBookId: not null }:
                    _editorModelRequestKey = null;
                    await LoadAuthorBookAsync(request.AuthorBookId.Value, version, cancellationToken);
                    break;
                case { Source: BookModalSource.User, Mode: BookModalMode.Create }:
                    EnsureCreateEditorModel(request);
                    break;
                case { Source: BookModalSource.User, UserBookId: not null }:
                    await LoadUserBookAsync(request.UserBookId.Value, request, version, cancellationToken);
                    break;
                default:
                    Error = "This book link is invalid.";
                    break;
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // Navigation or disposal canceled a stale load; the current route owns modal errors.
        }
        catch (Exception ex)
        {
            if (IsCurrentLoad(version, cancellationToken))
            {
                _logger.LogWarning(ex, "Book modal load failed for {BookModalUri}", _uri);
                Error = "Book details could not be loaded.";
            }
        }
        finally
        {
            if (IsCurrentLoad(version, cancellationToken))
            {
                Loading = false;
                NotifyChanged();
            }

            CompleteLoad(loadCancellation);
        }
    }

    private async Task LoadAuthorBookAsync(int authorBookId, int version, CancellationToken cancellationToken)
    {
        if (Request?.Mode is not BookModalMode.View)
        {
            Error = "Author books can only be viewed.";
            return;
        }

        var book = await _authorBooks.GetByIdAsync(new GetAuthorBookRequest { Id = authorBookId }, cancellationToken);
        if (!IsCurrentLoad(version, cancellationToken))
        {
            return;
        }

        if (book is null)
        {
            Error = "This book could not be found.";
            return;
        }

        ViewModel = new BookModalViewModel(book.Title, book.Author, book.Url);
    }

    private async Task LoadUserBookAsync(
        int id,
        BookModalRouteState request,
        int version,
        CancellationToken cancellationToken)
    {
        var response = await _books.GetByIdAsync(new GetBookRequest { Id = id }, cancellationToken);
        if (!IsCurrentLoad(version, cancellationToken))
        {
            return;
        }

        if (response is null)
        {
            Error = "This book could not be found.";
            return;
        }

        if (request.Mode is BookModalMode.Edit)
        {
            var key = request.EditorRequestKey;
            if (!string.Equals(_editorModelRequestKey, key, StringComparison.Ordinal))
            {
                EditorModel = new BookPageEditorModel
                {
                    Title = response.Title,
                    Author = response.Author,
                    Url = response.Url
                };
                _editorModelRequestKey = key;
            }

            return;
        }

        _editorModelRequestKey = null;
        ViewModel = new BookModalViewModel(response.Title, response.Author, response.Url);
    }

    public async Task SaveAsync(BookPageEditorModel model)
    {
        if (Saving)
        {
            return;
        }

        var request = Request;
        if (request is null)
        {
            return;
        }

        var operation = StartOperation();
        var cancellationToken = operation.Token;
        Saving = true;
        SaveError = null;
        NotifyChanged();

        try
        {
            if (request.Mode is BookModalMode.Create)
            {
                var created = await _books.CreateAsync(new CreateBookRequest
                {
                    Title = model.Title,
                    Author = NormalizeOptional(model.Author),
                    Url = NormalizeOptional(model.Url)
                }, cancellationToken);
                if (!IsCurrentOperation(operation))
                {
                    return;
                }

                _userBooks.ApplySavedBook(ToBookListItem(created));
            }
            else if (request is { Mode: BookModalMode.Edit, UserBookId: not null })
            {
                var title = model.Title.Trim();
                var author = NormalizeOptional(model.Author);
                var url = NormalizeOptional(model.Url);
                var success = await _books.UpdateAsync(new UpdateBookRequest
                {
                    Id = request.UserBookId.Value,
                    Title = title,
                    Author = author,
                    Url = url
                }, cancellationToken);
                if (!IsCurrentOperation(operation))
                {
                    return;
                }

                if (!success)
                {
                    SaveError = "Book not found.";
                    return;
                }

                _userBooks.ApplySavedBook(new BookListItemResponse
                {
                    Id = request.UserBookId.Value,
                    Title = title,
                    Author = author,
                    Url = url
                });
            }

            _navigate("/books", false);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // Navigation canceled this operation; do not show its result on a later route.
        }
        catch (Exception ex)
        {
            if (IsCurrentOperation(operation))
            {
                _logger.LogWarning(ex, "Book save failed for {BookModalUri}", _uri);
                SaveError = "Book could not be saved.";
            }
        }
        finally
        {
            if (IsCurrentOperation(operation))
            {
                Saving = false;
            }

            CompleteOperation(operation);
        }
    }

    public void RequestDelete()
    {
        if (CanDelete)
        {
            ConfirmingDelete = true;
        }
    }

    public void CancelDelete() => ConfirmingDelete = false;

    public async Task DeleteAsync()
    {
        if (Deleting)
        {
            return;
        }

        var request = Request;
        if (request is not { Source: BookModalSource.User, UserBookId: not null })
        {
            return;
        }

        var operation = StartOperation();
        var cancellationToken = operation.Token;
        Deleting = true;
        Error = null;
        NotifyChanged();

        try
        {
            var deleted = await _userBooks.DeleteAsync(request.UserBookId.Value, cancellationToken);
            if (!IsCurrentOperation(operation))
            {
                return;
            }

            if (deleted)
            {
                _navigate("/books", false);
                return;
            }

            Error = "Book could not be deleted.";
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // Navigation canceled this operation; do not show its result on a later route.
        }
        catch (Exception ex)
        {
            if (IsCurrentOperation(operation))
            {
                _logger.LogWarning(ex, "Book delete failed for {BookModalUri}", _uri);
                Error = "Book could not be deleted.";
            }
        }
        finally
        {
            if (IsCurrentOperation(operation))
            {
                Deleting = false;
            }

            CompleteOperation(operation);
        }
    }

    private void EnsureCreateEditorModel(BookModalRouteState request)
    {
        var key = request.EditorRequestKey;
        if (string.Equals(_editorModelRequestKey, key, StringComparison.Ordinal))
        {
            return;
        }

        EditorModel = new BookPageEditorModel();
        _editorModelRequestKey = key;
    }

    private static string? NormalizeOptional(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value.Trim();

    private static BookListItemResponse ToBookListItem(CreateBookResponse response) => new()
    {
        Id = response.Id,
        Title = response.Title,
        Author = response.Author,
        Url = response.Url
    };

    private CancellationTokenSource StartLoad(out int version)
    {
        CancelActiveLoad();
        var cancellation = new CancellationTokenSource();
        _loadCancellation = cancellation;
        version = Interlocked.Increment(ref _loadVersion);
        return cancellation;
    }

    private bool IsCurrentLoad(int version, CancellationToken cancellationToken) =>
        !cancellationToken.IsCancellationRequested && version == Volatile.Read(ref _loadVersion);

    private void CompleteLoad(CancellationTokenSource loadCancellation)
    {
        if (ReferenceEquals(_loadCancellation, loadCancellation))
        {
            _loadCancellation = null;
        }

        loadCancellation.Dispose();
    }

    private void CancelActiveLoad()
    {
        var cancellation = _loadCancellation;
        if (cancellation is null)
        {
            return;
        }

        _loadCancellation = null;
        cancellation.Cancel();
    }

    private CancellationTokenSource StartOperation()
    {
        CancelActiveOperation();
        var cancellation = new CancellationTokenSource();
        _operationCancellation = cancellation;
        return cancellation;
    }

    private bool IsCurrentOperation(CancellationTokenSource operation) =>
        !operation.IsCancellationRequested && ReferenceEquals(_operationCancellation, operation);

    private void CompleteOperation(CancellationTokenSource operation)
    {
        if (ReferenceEquals(_operationCancellation, operation))
        {
            _operationCancellation = null;
        }

        operation.Dispose();
    }

    private void CancelActiveOperation()
    {
        var cancellation = _operationCancellation;
        if (cancellation is null)
        {
            return;
        }

        _operationCancellation = null;
        cancellation.Cancel();
    }

    private void NotifyChanged() => Changed?.Invoke();

    public void Dispose()
    {
        CancelActiveLoad();
        CancelActiveOperation();
    }

    public sealed record BookModalViewModel(string Title, string? Author, string? Url);
}
