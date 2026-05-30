namespace BlazorAutoApp.Simulation.Running;

internal static class RunId
{
    public static string Create(DateTimeOffset startedAt, string target) =>
        $"{startedAt:yyyyMMdd-HHmmss}-{target}-{Guid.NewGuid():N}"[..40];

    public static string CreateSynthetic(DateTimeOffset startedAt) =>
        $"{startedAt:yyyyMMddTHHmmssZ}-{Guid.NewGuid():N}"[..25];
}
