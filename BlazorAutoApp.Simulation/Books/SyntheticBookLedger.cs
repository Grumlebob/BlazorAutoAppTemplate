using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Simulation.Reporting;

namespace BlazorAutoApp.Simulation.Books;

internal sealed class SyntheticBookLedger
{
    private readonly List<SyntheticBook> _books = [];

    public IReadOnlyList<SyntheticBook> Books => _books;

    public void Record(SyntheticBook book)
    {
        _books.Add(book);
    }

    public void RecordCreated(CreateBookResponse book) =>
        RecordApiBook(book.Id, book.Title, book.Author, book.Url, "created");

    public void RecordCreated(BookListItemResponse book) =>
        RecordApiBook(book.Id, book.Title, book.Author, book.Url, "created");

    public void RecordUpdated(GetBookResponse book) =>
        RecordApiBook(book.Id, book.Title, book.Author, book.Url, "updated");

    public void RecordUpdated(BookListItemResponse book) =>
        RecordApiBook(book.Id, book.Title, book.Author, book.Url, "updated");

    public void RecordDeleted(BookListItemResponse book) =>
        RecordApiBook(book.Id, book.Title, book.Author, book.Url, "deleted");

    public void RecordDeleted(int id, string title, string? author, string? url) =>
        RecordApiBook(id, title, author, url, "deleted");

    public IReadOnlyList<SyntheticLedgerEntry> ToReportEntries() =>
        _books
            .Select(static book => new SyntheticLedgerEntry(book.Id, book.Title, book.Author, book.Url, book.State))
            .ToArray();

    private void RecordApiBook(int id, string title, string? author, string? url, string state)
    {
        _books.Add(new SyntheticBook(id, title, author ?? "", url ?? "", state));
    }
}
