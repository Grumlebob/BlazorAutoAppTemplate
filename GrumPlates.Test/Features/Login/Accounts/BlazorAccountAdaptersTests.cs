using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.RegularExpressions;
using GrumPlates.Core.Features.Login.UseCases.Shared;
using GrumPlates.Features.Login.Account;
using GrumPlates.Infrastructure.Persistence;
using GrumPlates.Test.TestSupport.Accounts;
using GrumPlates.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace GrumPlates.Test.Features.Login.Accounts;

[Collection(TestCollectionNames.StartupIntegration)]
[Trait("FrontendProfile", "BlazorAuto")]
public sealed class BlazorAccountAdaptersTests
{
    private static readonly Dictionary<string, string?> EmailSettings = new()
    {
        ["Accounts:Email:Host"] = "localhost",
        ["Accounts:Email:Port"] = "1",
        ["Accounts:Email:From"] = "accounts@example.test",
        ["Accounts:Email:Security"] = "StartTls",
        ["Accounts:PublicOrigin"] = "https://books.example.test"
    };

    [Fact]
    public async Task EnabledRegistrationFormUsesEmailFirstOutboxAndGenericConfirmation()
    {
        var settings = new Dictionary<string, string?>(EmailSettings)
        {
            ["Accounts:RegistrationEnabled"] = "true"
        };
        await using var fixture = new RealCookieAccountFixture(settings);
        await fixture.InitializeAsync();
        using var client = fixture.CreateClient();

        using var page = await client.GetAsync("/Account/Register");
        Assert.Equal(HttpStatusCode.OK, page.StatusCode);
        var html = await page.Content.ReadAsStringAsync();
        Assert.Contains("Request registration", html, StringComparison.Ordinal);
        Assert.DoesNotContain("type=\"password\"", html, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("ExternalLoginPicker", html, StringComparison.Ordinal);

        var fields = ReadHiddenInputs(html);
        fields["EmailInput.Email"] = $"{Guid.NewGuid():N}@example.test";
        using var response = await client.PostAsync("/Account/Register", new FormUrlEncodedContent(fields));

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.Contains("/Account/RegisterConfirmation", response.Headers.Location?.OriginalString, StringComparison.Ordinal);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByEmailAsync(fields["EmailInput.Email"]);
            Assert.NotNull(user);
            Assert.False(user.EmailConfirmed);
            Assert.Null(user.PasswordHash);
        }

        using var confirmation = await client.GetAsync(response.Headers.Location);
        Assert.Equal(HttpStatusCode.OK, confirmation.StatusCode);
        var confirmationHtml = await confirmation.Content.ReadAsStringAsync();
        Assert.Contains("if applicable", confirmationHtml, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("email has been sent", confirmationHtml, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task EnabledConfirmationGetDoesNotConsumeProofAndPostRedirectsWithoutSecrets()
    {
        await using var fixture = new RealCookieAccountFixture(EmailSettings);
        await fixture.InitializeAsync();
        var account = await fixture.CreateUserAsync(confirmed: false);
        string token;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id) ?? throw new InvalidOperationException("Fixture user missing.");
            token = await users.GenerateEmailConfirmationTokenAsync(user);
        }

        var encodedToken = WebEncoders.Base64UrlEncode(Encoding.UTF8.GetBytes(token));
        var callbackPath = $"/Account/ConfirmEmail?userId={Uri.EscapeDataString(account.Id)}&code={Uri.EscapeDataString(encodedToken)}";
        using var client = fixture.CreateClient();
        using var page = await client.GetAsync(callbackPath);

        Assert.Equal(HttpStatusCode.OK, page.StatusCode);
        var html = await page.Content.ReadAsStringAsync();
        Assert.Contains("Confirm email and create account", html, StringComparison.Ordinal);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.False(user.EmailConfirmed);
            Assert.True(await users.CheckPasswordAsync(user, account.Password));
        }

        var fields = ReadHiddenInputs(html);
        var newPassword = $"Fresh-{Guid.NewGuid():N}-Password";
        fields["Input.UserId"] = account.Id;
        fields["Input.Code"] = token;
        fields["Input.NewPassword"] = newPassword;
        fields["Input.ConfirmPassword"] = newPassword;
        using var response = await client.PostAsync(callbackPath, new FormUrlEncodedContent(fields));

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        var redirect = response.Headers.Location?.OriginalString ?? "";
        Assert.Contains("/Account/ConfirmEmail", redirect, StringComparison.Ordinal);
        Assert.DoesNotContain("code=", redirect, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(account.Id, redirect, StringComparison.Ordinal);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.True(user.EmailConfirmed);
            Assert.True(await users.CheckPasswordAsync(user, newPassword));
            Assert.False(await users.CheckPasswordAsync(user, account.Password));
        }
    }

    [Fact]
    public async Task EnabledRecoveryFormsKeepGenericResponsesAndDoNotBypassTwoFactorEligibility()
    {
        await using var fixture = new RealCookieAccountFixture(EmailSettings);
        await fixture.InitializeAsync();
        var account = await fixture.CreateUserAsync();
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id) ?? throw new InvalidOperationException("Fixture user missing.");
            Assert.True((await users.SetTwoFactorEnabledAsync(user, true)).Succeeded);
        }

        using var client = fixture.CreateClient();
        using var forgotPage = await client.GetAsync("/Account/ForgotPassword");
        Assert.Equal(HttpStatusCode.OK, forgotPage.StatusCode);
        var forgotFields = ReadHiddenInputs(await forgotPage.Content.ReadAsStringAsync());
        forgotFields["Input.Email"] = account.Email;
        using var forgot = await client.PostAsync("/Account/ForgotPassword", new FormUrlEncodedContent(forgotFields));
        Assert.Equal(HttpStatusCode.Redirect, forgot.StatusCode);
        Assert.Contains("/Account/ForgotPasswordConfirmation", forgot.Headers.Location?.OriginalString, StringComparison.Ordinal);
        using var genericConfirmation = await client.GetAsync(forgot.Headers.Location);
        var genericHtml = await genericConfirmation.Content.ReadAsStringAsync();
        Assert.Contains("if applicable", genericHtml, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("email has been sent", genericHtml, StringComparison.OrdinalIgnoreCase);

        string resetToken;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            Assert.True(await db.AccountOutbox.AnyAsync(message => message.UserId == account.Id && message.Purpose == "PasswordReset"));
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id) ?? throw new InvalidOperationException("Fixture user missing.");
            resetToken = await users.GeneratePasswordResetTokenAsync(user);
        }

        var encodedToken = WebEncoders.Base64UrlEncode(Encoding.UTF8.GetBytes(resetToken));
        var resetPath = $"/Account/ResetPassword?userId={Uri.EscapeDataString(account.Id)}&code={Uri.EscapeDataString(encodedToken)}";
        using var resetPage = await client.GetAsync(resetPath);
        Assert.Equal(HttpStatusCode.OK, resetPage.StatusCode);
        var resetFields = ReadHiddenInputs(await resetPage.Content.ReadAsStringAsync());
        var newPassword = $"Reset-{Guid.NewGuid():N}-Password";
        resetFields["Input.UserId"] = account.Id;
        resetFields["Input.Code"] = resetToken;
        resetFields["Input.Password"] = newPassword;
        resetFields["Input.ConfirmPassword"] = newPassword;
        using var completedReset = await client.PostAsync(resetPath, new FormUrlEncodedContent(resetFields));

        Assert.Equal(HttpStatusCode.Redirect, completedReset.StatusCode);
        Assert.Contains("/Account/ResetPasswordConfirmation", completedReset.Headers.Location?.OriginalString, StringComparison.Ordinal);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id) ?? throw new InvalidOperationException("Fixture user missing.");
            Assert.True(user.TwoFactorEnabled);
            Assert.False(await users.CheckPasswordAsync(user, account.Password));
            Assert.True(await users.CheckPasswordAsync(user, newPassword));
        }
        using var refusedReactLogin = await RealCookieAccountFixture.LoginAsync(client, account.Email, newPassword);
        Assert.Equal(HttpStatusCode.Unauthorized, refusedReactLogin.StatusCode);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
    }

    [Fact]
    public async Task EnabledEmailAndPasswordManagementFormsUseCurrentProofAndCleanConfirmationRedirect()
    {
        await using var fixture = new RealCookieAccountFixture(EmailSettings);
        await fixture.InitializeAsync();
        var account = await fixture.CreateUserAsync();
        var newEmail = $"{Guid.NewGuid():N}@example.test";
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, account.Email, account.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);

        using var emailPage = await client.GetAsync("/Account/Manage/Email");
        Assert.Equal(HttpStatusCode.OK, emailPage.StatusCode);
        var emailFields = ReadHiddenInputs(await emailPage.Content.ReadAsStringAsync());
        emailFields["Input.NewEmail"] = newEmail;
        emailFields["Input.Password"] = account.Password;
        using var emailRequest = await client.PostAsync("/Account/Manage/Email", new FormUrlEncodedContent(emailFields));
        Assert.Equal(HttpStatusCode.OK, emailRequest.StatusCode);
        var emailRequestHtml = await emailRequest.Content.ReadAsStringAsync();
        Assert.Contains("If this change can proceed", emailRequestHtml, StringComparison.Ordinal);
        Assert.DoesNotContain("email has been sent", emailRequestHtml, StringComparison.OrdinalIgnoreCase);

        string changeToken;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id) ?? throw new InvalidOperationException("Fixture user missing.");
            Assert.Equal(account.Email, user.Email);
            changeToken = await users.GenerateChangeEmailTokenAsync(user, newEmail);
        }

        var encodedChangeToken = WebEncoders.Base64UrlEncode(Encoding.UTF8.GetBytes(changeToken));
        var changePath = $"/Account/ConfirmEmailChange?userId={Uri.EscapeDataString(account.Id)}&email={Uri.EscapeDataString(newEmail)}&code={Uri.EscapeDataString(encodedChangeToken)}";
        using var confirmPage = await client.GetAsync(changePath);
        Assert.Equal(HttpStatusCode.OK, confirmPage.StatusCode);
        var confirmFields = ReadHiddenInputs(await confirmPage.Content.ReadAsStringAsync());
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var user = await scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>().FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.Equal(account.Email, user.Email);
        }

        confirmFields["Input.UserId"] = account.Id;
        confirmFields["Input.Email"] = newEmail;
        confirmFields["Input.Code"] = changeToken;
        using var confirmed = await client.PostAsync(changePath, new FormUrlEncodedContent(confirmFields));
        Assert.Equal(HttpStatusCode.Redirect, confirmed.StatusCode);
        var confirmRedirect = confirmed.Headers.Location?.OriginalString ?? "";
        Assert.DoesNotContain("code=", confirmRedirect, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(account.Id, confirmRedirect, StringComparison.Ordinal);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);

        using var relogin = await RealCookieAccountFixture.LoginAsync(client, newEmail, account.Password);
        Assert.Equal(HttpStatusCode.OK, relogin.StatusCode);
        using var passwordPage = await client.GetAsync("/Account/Manage/ChangePassword");
        Assert.Equal(HttpStatusCode.OK, passwordPage.StatusCode);
        var passwordFields = ReadHiddenInputs(await passwordPage.Content.ReadAsStringAsync());
        var updatedPassword = $"Changed-{Guid.NewGuid():N}-Password";
        passwordFields["Input.OldPassword"] = account.Password;
        passwordFields["Input.NewPassword"] = updatedPassword;
        passwordFields["Input.ConfirmPassword"] = updatedPassword;
        using var changedPassword = await client.PostAsync("/Account/Manage/ChangePassword", new FormUrlEncodedContent(passwordFields));
        Assert.Equal(HttpStatusCode.Redirect, changedPassword.StatusCode);
        Assert.Contains("/Account/Login", changedPassword.Headers.Location?.OriginalString, StringComparison.Ordinal);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.Equal(newEmail, user.Email);
            Assert.True(await users.CheckPasswordAsync(user, updatedPassword));
            Assert.False(await users.CheckPasswordAsync(user, account.Password));
        }
    }

    [Fact]
    public async Task EnabledDeleteFormRequiresCurrentPasswordAndRemovesTheAccount()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var account = await fixture.CreateUserAsync();
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, account.Email, account.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);

        using var page = await client.GetAsync("/Account/Manage/DeletePersonalData");
        Assert.Equal(HttpStatusCode.OK, page.StatusCode);
        var fields = ReadHiddenInputs(await page.Content.ReadAsStringAsync());
        fields["Input.Password"] = "incorrect password";
        using (var rejected = await client.PostAsync("/Account/Manage/DeletePersonalData", new FormUrlEncodedContent(fields)))
        {
            Assert.Equal(HttpStatusCode.OK, rejected.StatusCode);
            using var scope = fixture.Factory.Services.CreateScope();
            Assert.NotNull(await scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>().FindByIdAsync(account.Id));
        }

        fields["Input.Password"] = account.Password;
        using var deleted = await client.PostAsync("/Account/Manage/DeletePersonalData", new FormUrlEncodedContent(fields));
        Assert.Equal(HttpStatusCode.Redirect, deleted.StatusCode);
        Assert.Contains("/Account/Login", deleted.Headers.Location?.OriginalString, StringComparison.Ordinal);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using var verifyScope = fixture.Factory.Services.CreateScope();
        Assert.Null(await verifyScope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>().FindByIdAsync(account.Id));
    }

    [Fact]
    public async Task EnabledPersonalDataDownloadRequiresPasswordAndUsesBoundedExportContract()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var account = await fixture.CreateUserAsync();
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, account.Email, account.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);

        using var page = await client.GetAsync("/Account/Manage/PersonalData");
        Assert.Equal(HttpStatusCode.OK, page.StatusCode);
        var html = await page.Content.ReadAsStringAsync();
        Assert.Contains("name=\"Password\"", html, StringComparison.Ordinal);
        Assert.Contains("maxlength=\"256\"", html, StringComparison.Ordinal);
        var fields = ReadHiddenInputs(html);

        fields["Password"] = "incorrect password";
        using (var rejected = await client.PostAsync("/Account/Manage/DownloadPersonalData", new FormUrlEncodedContent(fields)))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, rejected.StatusCode);
        }

        fields["Password"] = account.Password;
        using var response = await client.PostAsync("/Account/Manage/DownloadPersonalData", new FormUrlEncodedContent(fields));

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Contains("AccountExport.json", response.Content.Headers.ContentDisposition?.ToString(), StringComparison.Ordinal);
        var export = await response.Content.ReadFromJsonAsync<AccountExport>();
        Assert.NotNull(export);
        Assert.Equal(account.Id, export.User.Id);
        Assert.Equal(account.Email, export.User.Email);
        var json = await response.Content.ReadAsStringAsync();
        Assert.DoesNotContain("Authenticator", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("SecurityStamp", json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("PasswordHash", json, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task EnabledBlazorRetainsAdvancedSignInAndManagementRoutes()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var account = await fixture.CreateUserAsync();
        using var client = fixture.CreateClient();
        using var login = await RealCookieAccountFixture.LoginAsync(client, account.Email, account.Password);
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);

        using var loginPage = await client.GetAsync("/Account/Login");
        Assert.Equal(HttpStatusCode.OK, loginPage.StatusCode);
        var html = await loginPage.Content.ReadAsStringAsync();
        Assert.Contains("Log in with a passkey", html, StringComparison.Ordinal);
        Assert.Contains("Use another service to log in", html, StringComparison.Ordinal);

        foreach (var path in new[]
        {
            "/Account/Manage/TwoFactorAuthentication",
            "/Account/Manage/Passkeys",
            "/Account/Manage/ExternalLogins"
        })
        {
            using var response = await client.GetAsync(path);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        }

        var session = await RealCookieAccountFixture.ReadSessionAsync(client);
        foreach (var path in new[] { "/Account/PasskeyCreationOptions", "/Account/PasskeyRequestOptions" })
        {
            using var missingCsrf = await client.PostAsync(path, new FormUrlEncodedContent([]));
            Assert.Equal(HttpStatusCode.BadRequest, missingCsrf.StatusCode);
            using var request = new HttpRequestMessage(HttpMethod.Post, path) { Content = new FormUrlEncodedContent([]) };
            request.Headers.Add("X-CSRF-TOKEN", session.CsrfToken);
            using var response = await client.SendAsync(request);
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            using var options = System.Text.Json.JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            Assert.False(string.IsNullOrEmpty(options.RootElement.GetProperty("challenge").GetString()));
        }
    }

    [Fact]
    public async Task EnabledBlazorRequiresTwoFactorBeforeIssuingARealCookieAndRetainsManagement()
    {
        await using var fixture = new RealCookieAccountFixture();
        await fixture.InitializeAsync();
        var account = await fixture.CreateUserAsync();
        string recoveryCode;
        using (var scope = fixture.Factory.Services.CreateScope())
        {
            var users = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
            var user = await users.FindByIdAsync(account.Id);
            Assert.NotNull(user);
            Assert.True((await users.ResetAuthenticatorKeyAsync(user)).Succeeded);
            Assert.True((await users.SetTwoFactorEnabledAsync(user, true)).Succeeded);
            recoveryCode = (await users.GenerateNewTwoFactorRecoveryCodesAsync(user, 2))!.First();
        }

        using var client = fixture.CreateClient();
        using var refusedReact = await RealCookieAccountFixture.LoginAsync(client, account.Email, account.Password);
        Assert.Equal(HttpStatusCode.Unauthorized, refusedReact.StatusCode);
        const string loginPath = "/Account/Login?ReturnUrl=%2FAccount%2FManage";
        using var loginPage = await client.GetAsync(loginPath);
        var fields = ReadHiddenInputs(await loginPage.Content.ReadAsStringAsync());
        fields["Input.Email"] = account.Email;
        fields["Input.Password"] = account.Password;
        using var passwordStep = await client.PostAsync(loginPath, new FormUrlEncodedContent(fields));
        Assert.Equal(HttpStatusCode.Redirect, passwordStep.StatusCode);
        Assert.Contains("/Account/LoginWith2fa", passwordStep.Headers.Location?.OriginalString, StringComparison.Ordinal);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using var authenticatorPage = await client.GetAsync(passwordStep.Headers.Location);
        Assert.Equal(HttpStatusCode.OK, authenticatorPage.StatusCode);
        Assert.Contains("Authenticator code", await authenticatorPage.Content.ReadAsStringAsync(), StringComparison.Ordinal);

        const string recoveryPath = "/Account/LoginWithRecoveryCode?ReturnUrl=%2FAccount%2FManage";
        using var recoveryPage = await client.GetAsync(recoveryPath);
        fields = ReadHiddenInputs(await recoveryPage.Content.ReadAsStringAsync());
        fields["Input.RecoveryCode"] = "invalid-fixture-recovery-code";
        using var invalidProof = await client.PostAsync(recoveryPath, new FormUrlEncodedContent(fields));
        Assert.Equal(HttpStatusCode.OK, invalidProof.StatusCode);
        var invalidHtml = await invalidProof.Content.ReadAsStringAsync();
        Assert.Contains("Invalid recovery code", invalidHtml, StringComparison.Ordinal);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        fields = ReadHiddenInputs(invalidHtml);
        fields["Input.RecoveryCode"] = recoveryCode;
        using var completed = await client.PostAsync(recoveryPath, new FormUrlEncodedContent(fields));
        Assert.Equal(HttpStatusCode.Redirect, completed.StatusCode);
        Assert.Equal(account.Id, (await RealCookieAccountFixture.ReadSessionAsync(client)).User?.Id);

        using var dataPage = await client.GetAsync("/Account/Manage/PersonalData");
        fields = ReadHiddenInputs(await dataPage.Content.ReadAsStringAsync());
        fields["Password"] = account.Password;
        using var exported = await client.PostAsync("/Account/Manage/DownloadPersonalData", new FormUrlEncodedContent(fields));
        Assert.Equal(HttpStatusCode.OK, exported.StatusCode);

        using var changePage = await client.GetAsync("/Account/Manage/ChangePassword");
        fields = ReadHiddenInputs(await changePage.Content.ReadAsStringAsync());
        var newPassword = $"Changed MFA password {Guid.NewGuid():N}";
        fields["Input.OldPassword"] = account.Password;
        fields["Input.NewPassword"] = newPassword;
        fields["Input.ConfirmPassword"] = newPassword;
        using var changed = await client.PostAsync("/Account/Manage/ChangePassword", new FormUrlEncodedContent(fields));
        Assert.Equal(HttpStatusCode.Redirect, changed.StatusCode);
        Assert.Null((await RealCookieAccountFixture.ReadSessionAsync(client)).User);
        using var stillRefusedReact = await RealCookieAccountFixture.LoginAsync(client, account.Email, newPassword);
        Assert.Equal(HttpStatusCode.Unauthorized, stillRefusedReact.StatusCode);
        using var verification = fixture.Factory.Services.CreateScope();
        var verifiedUsers = verification.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var remaining = await verifiedUsers.FindByIdAsync(account.Id);
        Assert.NotNull(remaining);
        Assert.True(remaining.TwoFactorEnabled);
        Assert.Equal(1, await verifiedUsers.CountRecoveryCodesAsync(remaining));
    }

    private static Dictionary<string, string> ReadHiddenInputs(string html)
    {
        var fields = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (Match input in Regex.Matches(html, "<input\\b[^>]*\\btype=\"hidden\"[^>]*>", RegexOptions.IgnoreCase | RegexOptions.Singleline))
        {
            var name = Regex.Match(input.Value, "\\bname=\"([^\"]*)\"", RegexOptions.IgnoreCase);
            var value = Regex.Match(input.Value, "\\bvalue=\"([^\"]*)\"", RegexOptions.IgnoreCase);
            if (name.Success)
            {
                fields[WebUtility.HtmlDecode(name.Groups[1].Value)] = value.Success
                    ? WebUtility.HtmlDecode(value.Groups[1].Value)
                    : "";
            }
        }
        return fields;
    }
}
