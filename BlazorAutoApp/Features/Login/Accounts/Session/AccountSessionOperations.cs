using BlazorAutoApp.Core.Features.Login.UseCases.Shared;
using BlazorAutoApp.Features.Login.Account;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Identity;

namespace BlazorAutoApp.Features.Login.Accounts.Session;

internal sealed class AccountSessionOperations(
    UserManager<ApplicationUser> users,
    SignInManager<ApplicationUser> signIn,
    IHttpContextAccessor accessor,
    IAntiforgery antiforgery,
    AccountOptions options,
    TimeProvider clock)
{
    private HttpContext Context => accessor.HttpContext ?? throw new InvalidOperationException("An account request requires an HTTP context.");

    public async Task<IResult> SessionAsync()
    {
        var user = await users.GetUserAsync(Context.User);
        var profile = user is null ? null : new AccountProfile(user.Id, user.Email ?? "", (await users.GetRolesAsync(user)).ToArray());
        var token = antiforgery.GetAndStoreTokens(Context).RequestToken!;
        return Results.Ok(new AccountSession(true, options.RegistrationEnabled, options.EmailEnabled, token, profile));
    }

    public async Task<IResult> LoginAsync(AccountLoginRequest request)
    {
        var user = await users.FindByEmailAsync(request.Email.Trim());
        if (user is null || user.TwoFactorEnabled)
        {
            return CredentialsRejected();
        }
        var result = await signIn.CheckPasswordSignInAsync(user, request.Password, lockoutOnFailure: true);
        if (!result.Succeeded)
        {
            return CredentialsRejected();
        }
        await signIn.SignInAsync(user, new AuthenticationProperties
        {
            IsPersistent = request.RememberMe,
            AllowRefresh = false,
            ExpiresUtc = clock.GetUtcNow().Add(request.RememberMe ? TimeSpan.FromDays(14) : TimeSpan.FromHours(8))
        });
        return Results.Ok(new AccountMessage("Signed in."));
    }

    public async Task<IResult> LogoutAsync()
    {
        await signIn.SignOutAsync();
        return Results.Ok(new AccountMessage("Signed out."));
    }

    private static IResult CredentialsRejected() => Results.Problem(statusCode: 401,
        title: "Sign-in failed", detail: "Check your credentials and account confirmation, then try again.",
        extensions: new Dictionary<string, object?> { ["code"] = "CredentialsInvalid" });
}
