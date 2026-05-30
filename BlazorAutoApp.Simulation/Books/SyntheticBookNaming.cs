using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Simulation.Running;

namespace BlazorAutoApp.Simulation.Books;

internal static class SyntheticBookNaming
{
    public const string Author = "Traffic Simulation";
    public const string UrlPrefix = "https://simulation.invalid/books/";

    public static string CreateRunId(DateTimeOffset startedAt) =>
        RunId.CreateSynthetic(startedAt);

    public static SyntheticBook Create(string target, string runId, string scenario, int sequence)
    {
        var title = $"[sim-v2:{target}:{runId}] {scenario} {sequence:0000}";
        var url = $"{UrlPrefix}{target}/{runId}/{sequence:0000}";
        return new SyntheticBook(null, title, Author, url, "planned");
    }

    public static bool IsSafeToDelete(BookListItemResponse book, string target) =>
        IsSafeToDelete(book.Title, book.Url, target);

    public static bool IsSafeToDelete(SyntheticBook book, string target) =>
        IsSafeToDelete(book.Title, book.Url, target);

    public static bool IsSafeToDelete(string title, string? url, string target)
    {
        return CleanupTargets(target).Any(candidate => title.StartsWith($"[sim-v2:{candidate}:", StringComparison.Ordinal))
            && !string.IsNullOrWhiteSpace(url)
            && url.StartsWith(UrlPrefix, StringComparison.Ordinal);
    }

    private static IEnumerable<string> CleanupTargets(string target) =>
        target switch
        {
            "localcluster-public" => ["localcluster-public", "localcluster-edge"],
            "cloud-public" => ["cloud-public", "cloud-edge"],
            _ => [target]
        };
}
