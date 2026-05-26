using System.Security.Claims;
using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.Domain;
using BlazorAutoApp.Core.Features.Books.UseCases.DeleteBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Logging;

namespace BlazorAutoApp.Client.Features.Books.UserBookcase;

public sealed class UserBookcaseState(
    IBooksApi books,
    AuthenticationStateProvider authenticationStateProvider,
    ILogger<UserBookcaseState> logger)
{
    private readonly IBooksApi _books = books;
    private readonly AuthenticationStateProvider _authenticationStateProvider = authenticationStateProvider;
    private readonly ILogger<UserBookcaseState> _logger = logger;
    private int _version;

    public event Action? Changed;

    public bool IsLoading { get; private set; } = true;

    public string? Error { get; private set; }

    public string? CurrentUserId { get; private set; }

    public IReadOnlyList<Book> Books { get; private set; } = [];

    public async Task LoadForCurrentUserAsync(bool forceRefresh = true, CancellationToken cancellationToken = default)
    {
        var version = Interlocked.Increment(ref _version);
        IsLoading = true;
        Error = null;
        NotifyChanged();

        var authState = await _authenticationStateProvider.GetAuthenticationStateAsync();
        var userId = GetUserKey(authState.User);
        if (string.IsNullOrWhiteSpace(userId))
        {
            ApplyLoadResult(version, null, []);
            return;
        }

        try
        {
            var response = await _books.GetAsync(new GetBooksRequest { ForceRefresh = forceRefresh }, cancellationToken);
            ApplyLoadResult(version, userId, response.Books);
        }
        catch (Exception ex)
        {
            if (version != Volatile.Read(ref _version))
            {
                return;
            }

            _logger.LogWarning(ex, "User bookcase load failed for user {UserId}", userId);
            CurrentUserId = userId;
            Error = "Your bookcase could not be loaded.";
            IsLoading = false;
            NotifyChanged();
        }
    }

    public void ApplySavedBook(Book savedBook)
    {
        Interlocked.Increment(ref _version);
        var next = Books
            .Where(book => book.Id != savedBook.Id)
            .Append(savedBook)
            .OrderBy(book => book.Id)
            .ToList();

        Books = next;
        IsLoading = false;
        Error = null;
        NotifyChanged();
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default)
    {
        var version = Interlocked.Increment(ref _version);
        try
        {
            var success = await _books.DeleteAsync(new DeleteBookRequest { Id = id }, cancellationToken);
            if (!success)
            {
                return false;
            }

            if (version == Volatile.Read(ref _version))
            {
                Books = Books.Where(book => book.Id != id).ToList();
                IsLoading = false;
                Error = null;
                NotifyChanged();
            }

            return true;
        }
        catch (Exception ex)
        {
            if (version == Volatile.Read(ref _version))
            {
                _logger.LogWarning(ex, "User book delete failed for book {BookId}", id);
                Error = "Book could not be deleted.";
                IsLoading = false;
                NotifyChanged();
            }

            return false;
        }
    }

    private void ApplyLoadResult(int version, string? userId, IReadOnlyList<Book> books)
    {
        if (version != Volatile.Read(ref _version))
        {
            return;
        }

        CurrentUserId = userId;
        Books = books.OrderBy(book => book.Id).ToList();
        Error = null;
        IsLoading = false;
        NotifyChanged();
    }

    private void NotifyChanged() => Changed?.Invoke();

    private static string? GetUserKey(ClaimsPrincipal user)
    {
        if (user.Identity?.IsAuthenticated != true)
        {
            return null;
        }

        return user.FindFirst(ClaimTypes.NameIdentifier)?.Value ??
               user.FindFirst(ClaimTypes.Name)?.Value ??
               user.Identity.Name;
    }
}
