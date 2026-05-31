# BlazorAutoApp.Simulation

Synthetic traffic generator for the Books app.

Prefer the repo Scripts entrypoint:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile smoke
```

Raw command:

```powershell
dotnet run --project .\BlazorAutoApp.Simulation -- --target local --profile smoke
```

## Supported

- anonymous page traffic.
- anonymous author-book API traffic.
- health/readiness traffic.
- authenticated login check with real app cookies.
- authenticated synthetic book create/update/delete.
- cleanup-only for safe V2 synthetic books.
- optional one-user browser sampler for the add/edit/delete UI path.
- total RPS pacing.
- API-specific RPS pacing.
- authenticated write pacing.
- `429` classification and `Retry-After` backoff.
- JSON and Markdown reports under `artifacts/simulation`.

## Safety

- Deployed targets require `--allow-deployed`.
- Writes, cleanup, and registration require `--allow-write`.
- Passwords must come from an environment variable.
- Cleanup deletes only books with the V2 simulation title prefix and `https://simulation.invalid/books/` URL.
- The browser sampler is one low-rate user journey, not browser load testing.

## Options

```text
--target local|localcluster-public|cloud-public|origin-via-tunnel
--base-url https://...
--profile smoke|demo|soak-lite|burst
--duration 90s|10m|1h
--max-rps 2
--users 4
--api-rps-budget 0.8
--auth-write-rps-budget 0.2
--report-dir artifacts/simulation
--auth-check
--auth-email user@example.com
--auth-password-env SIMULATION_AUTH_PASSWORD
--register-synthetic-user
--writes
--cleanup
--cleanup-only
--browser-sampler
--install-browsers
--allow-deployed
--allow-write
--allow-rate-limit
--allow-burst
```

## Common Commands

Install Chromium for auth/browser modes:

```powershell
.\Scripts\RunSimulation.ps1 -InstallBrowsers
```

Local authenticated check without writes:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -AuthCheck
```

Local authenticated write smoke:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile smoke -Writes -AllowWrite -Duration 30s
```

Cleanup safe V2 synthetic books:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -CleanupOnly -AllowWrite
```

If a run reports cleanup leftovers, run cleanup-only for the same target. Cleanup deletes only books owned by the simulator user whose title starts with `[sim-v2:<target>:` and whose URL starts with `https://simulation.invalid/books/`.

## Exit Codes

```text
0 success
1 simulation completed but failed thresholds
2 invalid options or missing safety gate
3 target unavailable before traffic started
4 cleanup failed or left synthetic data behind
5 unexpected runtime error
```
