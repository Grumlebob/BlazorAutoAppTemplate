using System.Security.Claims;
using GrumPlates.Client.Features.Books.BookModal;
using GrumPlates.Client.Features.Books.BookPage;
using GrumPlates.Client.Features.Books.UserBookcase;
using GrumPlates.Core.Features.Books.Contracts;
using GrumPlates.Core.Features.Books.UseCases.CreateBook;
using GrumPlates.Core.Features.Books.UseCases.DeleteBook;
using GrumPlates.Core.Features.Books.UseCases.GetAuthorBook;
using GrumPlates.Core.Features.Books.UseCases.GetAuthorBooks;
using GrumPlates.Core.Features.Books.UseCases.GetBook;
using GrumPlates.Core.Features.Books.UseCases.GetBooks;
using GrumPlates.Core.Features.Books.UseCases.UpdateBook;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Logging.Abstractions;

namespace GrumPlates.Test.Features.Books.Client;

public sealed class BookModalLifecycleTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LoadAsync_OlderSuccessOrFailureCannotReplaceNewerBook(bool olderFails)
    {
        var older = new TaskCompletionSource<GetBookResponse?>(TaskCreationOptions.RunContinuationsAsynchronously);
        CancellationToken olderToken = default;
        var api = new StubBooksApi
        {
            Read = (request, token) =>
            {
                if (request.Id != 1) return Task.FromResult<GetBookResponse?>(Book(2, "Newer"));
                olderToken = token;
                return older.Task;
            }
        };
        var (lifecycle, _, navigation) = Create(api);
        using (lifecycle)
        {
            var first = Load(lifecycle, View(1));
            await Load(lifecycle, View(2));
            if (olderFails) older.SetException(new IOException("Synthetic old load failure"));
            else older.SetResult(Book(1, "Older"));
            await first;

            Assert.True(olderToken.IsCancellationRequested);
            Assert.Equal("Newer", lifecycle.ViewModel?.Title);
            Assert.Equal(2, lifecycle.Request?.UserBookId);
            Assert.Null(lifecycle.Error);
            Assert.False(lifecycle.Loading);
            Assert.Empty(navigation);
        }
    }

    [Fact]
    public async Task SaveAsync_NavigationCancelsOldSaveWithoutUpdatingCacheOrClosingNewBook()
    {
        var saved = new TaskCompletionSource<CreateBookResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        CancellationToken saveToken = default;
        var api = new StubBooksApi
        {
            Create = (_, token) => { saveToken = token; return saved.Task; }
        };
        var (lifecycle, userBooks, navigation) = Create(api);
        using (lifecycle)
        {
            await Load(lifecycle, new(BookModalSource.User, BookModalMode.Create, null, null));
            var save = lifecycle.SaveAsync(new BookPageEditorModel { Title = "Old draft" });
            await Load(lifecycle, View(42));
            saved.SetResult(new CreateBookResponse { Id = 7, Title = "Old draft" });
            await save;

            Assert.True(saveToken.IsCancellationRequested);
            Assert.Equal(42, lifecycle.Request?.UserBookId);
            Assert.Equal("Book 42", lifecycle.ViewModel?.Title);
            Assert.Empty(userBooks.ShelfBooks);
            Assert.Empty(navigation);
            Assert.Null(lifecycle.SaveError);
            Assert.False(lifecycle.Saving);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task DeleteAsync_OldCompletionCannotCloseOrShowAnErrorOnNewBook(bool deleted)
    {
        var deletion = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        int? requestedId = null;
        CancellationToken deleteToken = default;
        var api = new StubBooksApi
        {
            Delete = (request, token) =>
            {
                requestedId = request.Id;
                deleteToken = token;
                return deletion.Task;
            }
        };
        var (lifecycle, _, navigation) = Create(api);
        using (lifecycle)
        {
            await Load(lifecycle, View(7));
            var delete = lifecycle.DeleteAsync();
            await Load(lifecycle, View(42));
            deletion.SetResult(deleted);
            await delete;

            Assert.Equal(7, requestedId);
            Assert.True(deleteToken.IsCancellationRequested);
            Assert.Equal(42, lifecycle.Request?.UserBookId);
            Assert.Equal("Book 42", lifecycle.ViewModel?.Title);
            Assert.Empty(navigation);
            Assert.Null(lifecycle.Error);
            Assert.False(lifecycle.Deleting);
        }
    }

    [Fact]
    public async Task LoadAsync_SupersededAuthenticationCannotRedirectNewPublicBook()
    {
        var authentication = new TaskCompletionSource<AuthenticationState>(TaskCreationOptions.RunContinuationsAsynchronously);
        var (lifecycle, _, navigation) = Create(new StubBooksApi());
        using (lifecycle)
        {
            var oldLoad = lifecycle.LoadAsync(new(BookModalSource.User, BookModalMode.Create, null, null),
                authentication.Task, "https://example.test/books?bookMode=create");
            await Load(lifecycle, new(BookModalSource.Author, BookModalMode.View, 12, null));
            authentication.SetResult(new AuthenticationState(new ClaimsPrincipal(new ClaimsIdentity())));
            await oldLoad;

            Assert.Equal(BookModalSource.Author, lifecycle.Request?.Source);
            Assert.Equal("Author book", lifecycle.ViewModel?.Title);
            Assert.Empty(navigation);
            Assert.Null(lifecycle.Error);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task Dispose_CancelsOutstandingLoadOrSaveAndIgnoresItsLateResult(bool saving)
    {
        var read = new TaskCompletionSource<GetBookResponse?>(TaskCreationOptions.RunContinuationsAsynchronously);
        var saved = new TaskCompletionSource<CreateBookResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        CancellationToken observed = default;
        var api = new StubBooksApi
        {
            Read = (_, token) => { observed = token; return read.Task; },
            Create = (_, token) => { observed = token; return saved.Task; }
        };
        var (lifecycle, userBooks, navigation) = Create(api);
        Task pending;
        if (saving)
        {
            await Load(lifecycle, new(BookModalSource.User, BookModalMode.Create, null, null));
            pending = lifecycle.SaveAsync(new BookPageEditorModel { Title = "Disposed draft" });
        }
        else pending = Load(lifecycle, View(7));
        var notifications = 0;
        lifecycle.Changed += () => notifications++;
        lifecycle.Dispose();
        if (saving) saved.SetResult(new CreateBookResponse { Id = 7, Title = "Disposed draft" });
        else read.SetResult(Book(7, "Disposed load"));
        await pending;

        Assert.True(observed.IsCancellationRequested);
        Assert.Empty(navigation);
        Assert.Empty(userBooks.ShelfBooks);
        Assert.Null(lifecycle.ViewModel);
        Assert.Equal(0, notifications);
    }

    private static BookModalRouteState View(int id) => new(BookModalSource.User, BookModalMode.View, null, id);

    private static Task Load(BookModalLifecycle lifecycle, BookModalRouteState request) =>
        lifecycle.LoadAsync(request, Authentication(), "https://example.test/books");

    private static Task<AuthenticationState> Authentication() => Task.FromResult(new AuthenticationState(
        new ClaimsPrincipal(new ClaimsIdentity([new Claim(ClaimTypes.NameIdentifier, "modal-user")], "fixture"))));

    private static GetBookResponse Book(int id, string title) => new() { Id = id, Title = title };

    private static (BookModalLifecycle Lifecycle, UserBookcaseState UserBooks, List<string> Navigation) Create(StubBooksApi api)
    {
        var userBooks = new UserBookcaseState(api, new StubAuthentication(), NullLogger<UserBookcaseState>.Instance);
        var navigation = new List<string>();
        return (new BookModalLifecycle(api, new StubAuthorBooksApi(), userBooks, NullLogger.Instance,
            (uri, _) => navigation.Add(uri)), userBooks, navigation);
    }

    private sealed class StubAuthentication : AuthenticationStateProvider
    {
        public override Task<AuthenticationState> GetAuthenticationStateAsync() => Authentication();
    }

    private sealed class StubBooksApi : IBooksApi
    {
        public Func<GetBookRequest, CancellationToken, Task<GetBookResponse?>> Read { get; init; } =
            (request, _) => Task.FromResult<GetBookResponse?>(Book(request.Id, $"Book {request.Id}"));
        public Func<CreateBookRequest, CancellationToken, Task<CreateBookResponse>> Create { get; init; } =
            (_, _) => throw new NotSupportedException();
        public Func<DeleteBookRequest, CancellationToken, Task<bool>> Delete { get; init; } =
            (_, _) => throw new NotSupportedException();
        public Task<GetBookResponse?> GetByIdAsync(GetBookRequest req, CancellationToken cancellationToken = default) => Read(req, cancellationToken);
        public Task<CreateBookResponse> CreateAsync(CreateBookRequest req, CancellationToken cancellationToken = default) => Create(req, cancellationToken);
        public Task<bool> DeleteAsync(DeleteBookRequest req, CancellationToken cancellationToken = default) => Delete(req, cancellationToken);
        public Task<GetBooksResponse> GetAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        public Task<bool> UpdateAsync(UpdateBookRequest req, CancellationToken cancellationToken = default) => throw new NotSupportedException();
    }

    private sealed class StubAuthorBooksApi : IAuthorBooksApi
    {
        public Task<GetAuthorBookResponse?> GetByIdAsync(GetAuthorBookRequest req, CancellationToken cancellationToken = default) =>
            Task.FromResult<GetAuthorBookResponse?>(new() { SeedKey = "synthetic-author", Title = "Author book" });
        public Task<GetAuthorBooksResponse> GetAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
    }
}
