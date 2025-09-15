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
- $env:SENDGRID_API_KEY = "<key>"            # or set SendGrid__ApiKey
Aliases
- APP_URL is accepted as an alias for App:Url (App__Url) for hosts that prefer a single variable without nesting.

Aliases
- POSTGRES_PORT is supported as an alias for Database:Port.

Required settings (non-Development)
- Database:Host
- Database:Port (or POSTGRES_PORT)
- Database:Name
- Database:Username
- Database:Password
- Storage:HullImages:RootPath
- Redis:Configuration

If any required value remains `INJECT_THIS_IN_ORDER_TO_RUN` or empty, startup fails with a clear error listing missing keys.
To bypass this behavior (used by integration tests), set `BYPASS_REQUIRED_SETTINGS=1`.
Supplying a full `ConnectionStrings:DefaultConnection` also satisfies database requirements.

