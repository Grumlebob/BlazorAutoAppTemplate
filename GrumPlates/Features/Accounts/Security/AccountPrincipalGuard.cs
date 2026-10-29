using System.Security.Claims;
using GrumPlates.Features.Accounts;
using Microsoft.AspNetCore.Antiforgery;

namespace GrumPlates.Features.Accounts.Security;

internal sealed class ExpectedAccountUser;

internal static class AccountPrincipalGuard
{
    public static void UseAccountPrincipalGuards(this WebApplication app)
    {
        if (!app.Services.GetRequiredService<AccountOptions>().Enabled) return;

        app.Use(async (context, next) =>
        {
            // Endpoint metadata limits this guard to real private operations.
            // Unknown API routes must keep their ordinary 404 behavior.
            var endpoint = context.GetEndpoint();
            if (endpoint?.Metadata.GetMetadata<ExpectedAccountUser>() is not null)
            {
                var actual = context.User.FindFirstValue(ClaimTypes.NameIdentifier);
                if (context.User.Identity?.IsAuthenticated != true || string.IsNullOrEmpty(actual))
                {
                    await AccountProblem.Create(401, "AuthenticationRequired", "Sign-in required").ExecuteAsync(context);
                    return;
                }
                var expected = context.Request.Headers["X-Expected-User"];
                if (expected.Count != 1 || !string.Equals(expected[0], actual, StringComparison.Ordinal))
                {
                    await AccountProblem.Create(409, "AccountChanged", "Account changed",
                        "Refresh your session before continuing.").ExecuteAsync(context);
                    return;
                }
            }

            if (endpoint?.Metadata.GetMetadata<AccountRequestProtection>() is not null
                && !HttpMethods.IsGet(context.Request.Method)
                && !HttpMethods.IsHead(context.Request.Method))
            {
                var antiforgery = context.RequestServices.GetRequiredService<IAntiforgery>();
                if (!await antiforgery.IsRequestValidAsync(context))
                {
                    await AccountProblem.Create(400, "CsrfInvalid", "Invalid request token",
                        "Refresh your session and try again.").ExecuteAsync(context);
                    return;
                }
            }
            await next();
        });
    }
}
