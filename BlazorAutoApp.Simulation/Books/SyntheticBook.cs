namespace BlazorAutoApp.Simulation.Books;

internal sealed record SyntheticBook(
    int? Id,
    string Title,
    string Author,
    string Url,
    string State);
