Environment Variables

This app centralizes all environment-driven settings in `settings.defaults.json`.
Every key in that file is present with a placeholder value (`INJECT_THIS_IN_ORDER_TO_RUN`) to make it
obvious what needs to be configured. Real environment variables override these values.

How overrides work (order)
- settings.defaults.json
- appsettings.json + appsettings.{Environment}.json
- Environment variables (use `__` for nested keys; no prefix)

Examples (Windows PowerShell)
- $env:Database__Host = "localhost"
- $env:Database__Port = "5432"   # or 5433
- $env:Database__Name = "app"
- $env:Database__Username = "postgres"
- $env:Database__Password = "yourpassword"
- $env:Redis__Configuration = "localhost:6379"
- $env:Storage__HullImages__RootPath = "C:\\Data\\HullImages"
- $env:Serilog__SeqUrl = "http://seq:5341"   # optional

Aliases
- POSTGRES_PORT is supported as an alias for Database:Port.

Database configuration behavior
- If `ConnectionStrings:DefaultConnection` is provided (for example from `appsettings.json` or env var), it is used directly.
- If it is not provided, the app falls back to:
  - `Database__Host`
  - `Database__Port` (or `POSTGRES_PORT`)
  - `Database__Name`
  - `Database__Username`
  - `Database__Password`

Optional auth settings
- Google login is optional. It is only enabled when both are non-empty:
  - `Authentication__Google__ClientId`
  - `Authentication__Google__ClientSecret`

