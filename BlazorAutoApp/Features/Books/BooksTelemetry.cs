using System.Diagnostics;
using System.Diagnostics.Metrics;

namespace BlazorAutoApp.Features.Books;

internal static class BooksTelemetry
{
    public const string ActivitySourceName = "BlazorAutoApp.Books";
    public const string MeterName = "BlazorAutoApp.Books";

    private static readonly ActivitySource ActivitySource = new(ActivitySourceName);
    private static readonly Meter Meter = new(MeterName);
    private static readonly Counter<long> OperationCounter = Meter.CreateCounter<long>(
        "books.operations.total",
        unit: "{operation}",
        description: "Books API operations by low-cardinality operation and outcome.");
    private static readonly Histogram<double> OperationDuration = Meter.CreateHistogram<double>(
        "books.operation.duration",
        unit: "ms",
        description: "Books API operation duration by low-cardinality operation and outcome.");

    public static Activity? StartActivity(string operation)
    {
        var activity = ActivitySource.StartActivity($"books.{operation}", ActivityKind.Internal);
        activity?.SetTag("books.operation", operation);
        return activity;
    }

    public static long GetTimestamp() => Stopwatch.GetTimestamp();

    public static void Record(string operation, string outcome, long startTimestamp)
    {
        var tags = new TagList
        {
            { "books.operation", operation },
            { "books.outcome", outcome }
        };

        OperationCounter.Add(1, tags);
        OperationDuration.Record(GetElapsedMilliseconds(startTimestamp), tags);
        Activity.Current?.SetTag("books.outcome", outcome);
    }

    public static void RecordException(string operation, long startTimestamp, Exception exception)
    {
        Activity.Current?.SetStatus(ActivityStatusCode.Error, exception.GetType().Name);
        Activity.Current?.AddException(exception);
        Record(operation, "error", startTimestamp);
    }

    private static double GetElapsedMilliseconds(long startTimestamp)
    {
        return Stopwatch.GetElapsedTime(startTimestamp).TotalMilliseconds;
    }
}
