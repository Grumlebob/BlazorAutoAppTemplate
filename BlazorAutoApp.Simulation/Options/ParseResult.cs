namespace BlazorAutoApp.Simulation.Options;

internal sealed record ParseResult(SimulationOptions? Options, IReadOnlyList<string> Errors);
