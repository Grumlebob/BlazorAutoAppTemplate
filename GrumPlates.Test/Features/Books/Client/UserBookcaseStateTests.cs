using System.Security.Claims;
using GrumPlates.Client.Features.Books.UserBookcase;
using GrumPlates.Core.Features.Books.Contracts;
using GrumPlates.Core.Features.Books.UseCases.CreateBook;
using GrumPlates.Core.Features.Books.UseCases.DeleteBook;
using GrumPlates.Core.Features.Books.UseCases.GetBook;
using GrumPlates.Core.Features.Books.UseCases.GetBooks;
using GrumPlates.Core.Features.Books.UseCases.UpdateBook;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.Extensions.Logging.Abstractions;

namespace GrumPlates.Test.Features.Books.Client;

public sealed class UserBookcaseStateTests
{
    [Fact]
    public async Task LoadForCurrentUserAsync_IgnoresOlderResponseAfterNewerLoad()
    {
        var olderResponse = new TaskCompletionSource<GetBooksResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        var newerResponse = new TaskCompletionSource<GetBooksResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        var requestCount = 0;
        var api = new StubBooksApi
        {
            Get = _ => Interlocked.Increment(ref requestCount) switch
            {
                1 => olderResponse.Task,
                2 => newerResponse.Task,
                _ => throw new InvalidOperationException("Unexpected bookcase request.")
            }
        };
        var state = CreateState(api);

        var olderLoad = state.LoadForCurrentUserAsync();
        var newerLoad = state.LoadForCurrentUserAsync();
        newerResponse.SetResult(CreateResponse(CreateBook(2, "Newer")));
        await newerLoad;
        olderResponse.SetResult(CreateResponse(CreateBook(1, "Older")));
        await olderLoad;

        Assert.Equal(new[] { 2 }, state.ShelfBooks.Select(book => book.Id));
        Assert.Null(state.Error);
        Assert.False(state.IsLoading);
    }

    [Fact]
    public async Task DeleteAsync_ReturnsFalseAndPreservesBookWhenCanceled()
    {
        var api = new StubBooksApi
        {
            Delete = (_, cancellationToken) => Task.FromCanceled<bool>(cancellationToken)
        };
        var state = CreateState(api);
        state.ApplySavedBook(CreateBook(4, "Keep me"));
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        var deleted = await state.DeleteAsync(4, cancellation.Token);

        Assert.False(deleted);
        Assert.Equal(new[] { 4 }, state.ShelfBooks.Select(book => book.Id));
    }

    [Fact]
    public async Task DeleteAsync_UsesRequestedIdAndKeepsOtherBooks()
    {
        int? requestedId = null;
        var api = new StubBooksApi
        {
            Delete = (request, _) =>
            {
                requestedId = request.Id;
                return Task.FromResult(true);
            }
        };
        var state = CreateState(api);
        state.ApplySavedBook(CreateBook(4, "First"));
        state.ApplySavedBook(CreateBook(9, "Second"));

        var deleted = await state.DeleteAsync(4);

        Assert.True(deleted);
        Assert.Equal(4, requestedId);
        Assert.Equal(new[] { 9 }, state.ShelfBooks.Select(book => book.Id));
    }

    private static UserBookcaseState CreateState(StubBooksApi api) => new(
        api,
        new TestAuthenticationStateProvider(),
        NullLogger<UserBookcaseState>.Instance);

    private static GetBooksResponse CreateResponse(params BookListItemResponse[] books) => new()
    {
        Books = [.. books]
    };

    private static BookListItemResponse CreateBook(int id, string title) => new()
    {
        Id = id,
        Title = title
    };

    private sealed class TestAuthenticationStateProvider : AuthenticationStateProvider
    {
        private readonly AuthenticationState _authenticationState = new(
            new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim(ClaimTypes.NameIdentifier, "user-1")],
                authenticationType: "test")));

        public override Task<AuthenticationState> GetAuthenticationStateAsync() =>
            Task.FromResult(_authenticationState);
    }

    private sealed class StubBooksApi : IBooksApi
    {
        public Func<CancellationToken, Task<GetBooksResponse>> Get { get; init; } =
            _ => Task.FromResult(CreateResponse());

        public Func<DeleteBookRequest, CancellationToken, Task<bool>> Delete { get; init; } =
            (_, _) => Task.FromResult(false);

        public Task<GetBooksResponse> GetAsync(CancellationToken cancellationToken = default) =>
            Get(cancellationToken);

        public Task<GetBookResponse?> GetByIdAsync(GetBookRequest req, CancellationToken cancellationToken = default) =>
            throw new NotSupportedException();

        public Task<CreateBookResponse> CreateAsync(CreateBookRequest req, CancellationToken cancellationToken = default) =>
            throw new NotSupportedException();

        public Task<bool> UpdateAsync(UpdateBookRequest req, CancellationToken cancellationToken = default) =>
            throw new NotSupportedException();

        public Task<bool> DeleteAsync(DeleteBookRequest req, CancellationToken cancellationToken = default) =>
            Delete(req, cancellationToken);
    }
}
