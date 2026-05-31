namespace BlazorAutoApp.Simulation;

internal static class HelpText
{
    public static void WriteShort()
    {
        Console.Error.WriteLine("Use --help for all options.");
        Console.Error.WriteLine("Example: dotnet run --project ./BlazorAutoApp.Simulation -- --target local --profile smoke");
    }

    public static void Write()
    {
        Console.WriteLine("""
            Books traffic simulation

            Usage:
              dotnet run --project ./BlazorAutoApp.Simulation -- [options]

            Common options:
              --target <local|localcluster-public|cloud-public|origin-via-tunnel>
              --base-url <url>
              --profile <smoke|demo|soak-lite|burst>
              --duration <90s|10m|1h>
              --max-rps <number>
              --users <number>
              --api-rps-budget <number>
              --auth-write-rps-budget <number>
              --report-dir <path>
              --auth-check
              --auth-email <email>
              --auth-password-env <environment variable name>
              --register-synthetic-user
              --keep-synthetic-data
              --install-browsers
              --playwright-browser <chromium>
              --headed-browser
              --allow-deployed
              --allow-write
              --allow-rate-limit
              --allow-burst
              --yes

            Authenticated V2 options:
              --auth-check        Log in and verify authenticated /api/books without writes.
              --writes            Enable authenticated synthetic book create/update/delete.
              --cleanup           Force cleanup after a write run.
              --cleanup-only      Delete safe V2 synthetic books for the simulator user.
              --browser-sampler   Run one low-rate authenticated browser journey.

            Safety:
              Deployed targets require --allow-deployed.
              Writes, cleanup, and registration require --allow-write.
              Passwords must come from an environment variable, not a CLI value.

            Mutating modes:
              --writes
              --cleanup
              --cleanup-only
              --browser-sampler

            Environment gates:
              SIMULATION_ALLOW_DEPLOYED=1
              SIMULATION_ALLOW_BURST=1
              SIMULATION_ALLOW_WRITE=1
              SIMULATION_AUTH_EMAIL=<email>
              SIMULATION_AUTH_PASSWORD=<password>

            Preferred repo entrypoint:
              ./Scripts/RunSimulation.ps1 -Target local -Profile smoke
            """);
    }
}
