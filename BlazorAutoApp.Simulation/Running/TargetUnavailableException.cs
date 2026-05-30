namespace BlazorAutoApp.Simulation.Running;

internal sealed class TargetUnavailableException : Exception
{
    public TargetUnavailableException(string message)
        : base(message)
    {
    }
}
