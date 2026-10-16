using System.Text.Json;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Http.Extensions;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Primitives;
using BlazorAutoApp.Core.Features.Login.UseCases.Shared;
using BlazorAutoApp.Features.Login.Account;
using BlazorAutoApp.Features.Login.Account.Pages;
using BlazorAutoApp.Features.Login.Account.Pages.Manage;
using BlazorAutoApp.Features.Login.Accounts;
using BlazorAutoApp.Infrastructure.Hosting;

namespace Microsoft.AspNetCore.Routing;

internal static class IdentityComponentsEndpointRouteBuilderExtensions
{
    // These endpoints are required by the Identity Razor components defined in the /Features/Login/Account/Pages directory of this project.
    public static IEndpointConventionBuilder MapAdditionalIdentityEndpoints(this IEndpointRouteBuilder endpoints)
    {
        ArgumentNullException.ThrowIfNull(endpoints);

        var accountGroup = endpoints.MapGroup("/Account");
        var accountsEnabled = endpoints.ServiceProvider.GetRequiredService<AccountOptions>().Enabled;
        if (accountsEnabled)
        {
            accountGroup.RequireRateLimiting(AppRateLimiting.AccountWritePolicyName);
        }

        accountGroup.MapPost("/PerformExternalLogin", (
            HttpContext context,
            [FromServices] SignInManager<ApplicationUser> signInManager,
            [FromForm] string provider,
            [FromForm] string returnUrl) =>
        {
            IEnumerable<KeyValuePair<string, StringValues>> query = [
                new("ReturnUrl", returnUrl),
                new("Action", ExternalLogin.LoginCallbackAction)];

            var redirectUrl = UriHelper.BuildRelative(
                context.Request.PathBase,
                "/Account/ExternalLogin",
                QueryString.Create(query));

            var properties = signInManager.ConfigureExternalAuthenticationProperties(provider, redirectUrl);
            return TypedResults.Challenge(properties, [provider]);
        });

        var logout = accountGroup.MapPost("/Logout", async (
            [FromServices] SignInManager<ApplicationUser> signInManager,
            [FromForm] string? returnUrl) =>
        {
            await signInManager.SignOutAsync();
            var localReturnUrl = string.IsNullOrWhiteSpace(returnUrl)
                ? "/"
                : $"/{returnUrl.TrimStart('/')}";
            return TypedResults.LocalRedirect($"~{localReturnUrl}");
        })
        .RequireAuthorization();
        if (!accountsEnabled)
        {
            logout.DisableAntiforgery();
        }

        accountGroup.MapPost("/PasskeyCreationOptions", async (
            HttpContext context,
            [FromServices] UserManager<ApplicationUser> userManager,
            [FromServices] SignInManager<ApplicationUser> signInManager,
            [FromServices] IAntiforgery antiforgery) =>
        {
            if (!await antiforgery.IsRequestValidAsync(context))
            {
                return AccountProblem.Create(400, "CsrfInvalid", "The request could not be verified");
            }

            var user = await userManager.GetUserAsync(context.User);
            if (user is null)
            {
                return Results.NotFound("Unable to load the current user.");
            }

            var userId = await userManager.GetUserIdAsync(user);
            var userName = await userManager.GetUserNameAsync(user) ?? "User";
            var optionsJson = await signInManager.MakePasskeyCreationOptionsAsync(new()
            {
                Id = userId,
                Name = userName,
                DisplayName = userName
            });
            return TypedResults.Content(optionsJson, contentType: "application/json");
        });

        accountGroup.MapPost("/PasskeyRequestOptions", async (
            HttpContext context,
            [FromServices] UserManager<ApplicationUser> userManager,
            [FromServices] SignInManager<ApplicationUser> signInManager,
            [FromServices] IAntiforgery antiforgery,
            [FromQuery] string? username) =>
        {
            if (!await antiforgery.IsRequestValidAsync(context))
            {
                return AccountProblem.Create(400, "CsrfInvalid", "The request could not be verified");
            }

            var user = string.IsNullOrEmpty(username) ? null : await userManager.FindByNameAsync(username);
            var optionsJson = await signInManager.MakePasskeyRequestOptionsAsync(user);
            return TypedResults.Content(optionsJson, contentType: "application/json");
        });

        var manageGroup = accountGroup.MapGroup("/Manage").RequireAuthorization();

        manageGroup.MapPost("/LinkExternalLogin", async (
            HttpContext context,
            [FromServices] SignInManager<ApplicationUser> signInManager,
            [FromForm] string provider) =>
        {
            // Clear the existing external cookie to ensure a clean login process
            await context.SignOutAsync(IdentityConstants.ExternalScheme);

            var redirectUrl = UriHelper.BuildRelative(
                context.Request.PathBase,
                "/Account/Manage/ExternalLogins",
                QueryString.Create("Action", ExternalLogins.LinkLoginCallbackAction));

            var properties = signInManager.ConfigureExternalAuthenticationProperties(provider, redirectUrl, signInManager.UserManager.GetUserId(context.User));
            return TypedResults.Challenge(properties, [provider]);
        });

        if (accountsEnabled)
        {
            manageGroup.MapPost("/DownloadPersonalData", async (
                HttpContext context,
                [FromForm] AccountPasswordRequest request,
                [FromServices] AccountOperations accounts) =>
            {
                var operation = await accounts.ExportAsync(request);
                context.Response.OnStarting(() =>
                {
                    if (context.Response.StatusCode == StatusCodes.Status200OK)
                    {
                        context.Response.Headers.ContentDisposition = "attachment; filename=AccountExport.json";
                    }
                    return Task.CompletedTask;
                });
                await operation.ExecuteAsync(context);
                return TypedResults.Empty;
            });
        }
        else
        {
            var loggerFactory = endpoints.ServiceProvider.GetRequiredService<ILoggerFactory>();
            var downloadLogger = loggerFactory.CreateLogger("DownloadPersonalData");

            manageGroup.MapPost("/DownloadPersonalData", async (
                HttpContext context,
                [FromServices] UserManager<ApplicationUser> userManager) =>
            {
                var user = await userManager.GetUserAsync(context.User);
                if (user is null)
                {
                    return Results.NotFound("Unable to load the current user.");
                }

                var userId = await userManager.GetUserIdAsync(user);
                downloadLogger.LogInformation("User with ID '{UserId}' asked for their personal data.", userId);

                // Only include personal data for download
                var personalData = new Dictionary<string, string>();
                var personalDataProps = typeof(ApplicationUser).GetProperties().Where(
                    prop => Attribute.IsDefined(prop, typeof(PersonalDataAttribute)));
                foreach (var p in personalDataProps)
                {
                    personalData.Add(p.Name, p.GetValue(user)?.ToString() ?? "null");
                }

                var logins = await userManager.GetLoginsAsync(user);
                foreach (var l in logins)
                {
                    personalData.Add($"{l.LoginProvider} external login provider key", l.ProviderKey);
                }

                personalData.Add("Authenticator Key", (await userManager.GetAuthenticatorKeyAsync(user))!);
                var fileBytes = JsonSerializer.SerializeToUtf8Bytes(personalData);

                context.Response.Headers.TryAdd("Content-Disposition", "attachment; filename=PersonalData.json");
                return TypedResults.File(fileBytes, contentType: "application/json", fileDownloadName: "PersonalData.json");
            });
        }

        return accountGroup;
    }
}
