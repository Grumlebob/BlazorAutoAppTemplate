Environment Variables

This app centralizes all environment-driven settings in `settings.defaults.json`.
Every key in that file is present with a placeholder value (`INJECT_THIS_IN_ORDER_TO_RUN`) to make it
obvious what needs to be configured. Real environment variables override these values.

How overrides work (order)
- settings.defaults.json
- appsettings.json + appsettings.{Environment}.json
- Environment variables (prefix `APP_`, use `__` for nested keys)

Examples (Windows PowerShell)
- $env:APP_Database__Host = "localhost"
- $env:APP_Database__Port = "5432"   # or 5433
- $env:APP_Database__Name = "app"
- $env:APP_Database__Username = "postgres"
- $env:APP_Database__Password = "yourpassword"
- $env:APP_Redis__Configuration = "localhost:6379"
- $env:APP_Storage__HullImages__RootPath = "C:\\Data\\HullImages"
- $env:APP_Serilog__SeqUrl = "http://seq:5341"   # optional
- $env:SENDGRID_API_KEY = "<key>"                 # optional; also supports APP_SendGrid__ApiKey

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
To bypass this behavior (used by integration tests), set `APP_BYPASS_REQUIRED_SETTINGS=1`.
Supplying a full `ConnectionStrings:DefaultConnection` also satisfies database requirements.

