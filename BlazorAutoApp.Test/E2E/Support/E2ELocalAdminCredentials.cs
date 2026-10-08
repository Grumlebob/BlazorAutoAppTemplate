using System;

namespace BlazorAutoApp.Test.E2E.Support;

internal static class E2ELocalAdminCredentials
{
    private const string DefaultEmail = "admin@admin.com";
    private const string DefaultPassword = "Admin123";

    public static string Email =>
        GetConfiguredValue("E2E_LOCAL_ADMIN_EMAIL", "LocalAccounts__Admin__Email", DefaultEmail);

    public static string Password =>
        GetConfiguredValue("E2E_LOCAL_ADMIN_PASSWORD", "LocalAccounts__Admin__Password", DefaultPassword);

    private static string GetConfiguredValue(string testVariableName, string appVariableName, string fallback)
    {
        var testValue = Environment.GetEnvironmentVariable(testVariableName);
        if (!string.IsNullOrWhiteSpace(testValue))
        {
            return testValue;
        }

        var appValue = Environment.GetEnvironmentVariable(appVariableName);
        return string.IsNullOrWhiteSpace(appValue) ? fallback : appValue;
    }
}
