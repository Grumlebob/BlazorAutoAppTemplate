using BlazorAutoApp.Client.Features.Books.BookModal;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Client;

public sealed class BookModalRouteStateTests
{
    [Theory]
    [InlineData("https://example.test/books")]
    [InlineData("https://example.test/books?bookMode=unknown")]
    public void Parse_ReturnsNull_WhenNoSupportedModeIsPresent(string uri)
    {
        var state = BookModalRouteState.Parse(uri);

        Assert.Null(state);
    }

    [Fact]
    public void Parse_ReturnsCreateState()
    {
        var state = BookModalRouteState.Parse("https://example.test/books?bookMode=create");

        Assert.NotNull(state);
        Assert.Equal(BookModalSource.User, state!.Source);
        Assert.Equal(BookModalMode.Create, state.Mode);
        Assert.Null(state.AuthorBookId);
        Assert.Null(state.UserBookId);
        Assert.Equal("user:create", state.EditorRequestKey);
    }

    [Fact]
    public void Parse_ReturnsAuthorViewState()
    {
        var state = BookModalRouteState.Parse("https://example.test/books?authorBookId=42&bookMode=view");

        Assert.NotNull(state);
        Assert.Equal(BookModalSource.Author, state!.Source);
        Assert.Equal(BookModalMode.View, state.Mode);
        Assert.Equal(42, state.AuthorBookId);
        Assert.Null(state.UserBookId);
    }

    [Fact]
    public void Parse_ReturnsUserViewState()
    {
        var state = BookModalRouteState.Parse("https://example.test/books?bookId=17&bookMode=view");

        Assert.NotNull(state);
        Assert.Equal(BookModalSource.User, state!.Source);
        Assert.Equal(BookModalMode.View, state.Mode);
        Assert.Null(state.AuthorBookId);
        Assert.Equal(17, state.UserBookId);
    }

    [Fact]
    public void Parse_ReturnsUserEditState()
    {
        var state = BookModalRouteState.Parse("https://example.test/books?bookId=17&bookMode=edit");

        Assert.NotNull(state);
        Assert.Equal(BookModalSource.User, state!.Source);
        Assert.Equal(BookModalMode.Edit, state.Mode);
        Assert.Equal(17, state.UserBookId);
        Assert.Equal("user:edit:17", state.EditorRequestKey);
    }

    [Fact]
    public void Parse_DecodesQueryValues()
    {
        var state = BookModalRouteState.Parse("https://example.test/books?bookMode=VIEW&bookId=12");

        Assert.NotNull(state);
        Assert.Equal(BookModalMode.View, state!.Mode);
        Assert.Equal(12, state.UserBookId);
    }
}
