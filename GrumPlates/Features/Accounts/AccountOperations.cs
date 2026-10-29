using GrumPlates.Core.Features.Accounts.Contracts;
using GrumPlates.Features.Accounts.Management;
using GrumPlates.Features.Accounts.Recovery;
using GrumPlates.Features.Accounts.Registration;
using GrumPlates.Features.Accounts.Session;

namespace GrumPlates.Features.Accounts;

internal sealed class AccountOperations(
    IHttpContextAccessor accessor,
    AccountRegistrationHandler registration,
    AccountRecoveryHandler recovery,
    AccountRevocationHandler revocation,
    AccountPasswordChangeHandler passwordChanges,
    AccountEmailChangeHandler emailChanges,
    AccountExportHandler exports,
    AccountDeletionHandler deletions)
{
    private HttpContext Context => accessor.HttpContext ?? throw new InvalidOperationException("An account request requires an HTTP context.");

    public Task<IResult> RegisterAsync(AccountRegisterRequest request) => registration.RegisterAsync(request, Context.RequestAborted);
    public Task<IResult> ResendAsync(AccountEmailRequest request) => registration.ResendAsync(request, Context.RequestAborted);
    public Task<IResult> ConfirmAsync(AccountConfirmEmailRequest request) => registration.ConfirmAsync(request, Context.RequestAborted);
    public Task<IResult> ForgotAsync(AccountEmailRequest request) => recovery.ForgotAsync(request, Context.RequestAborted);
    public Task<IResult> ResetAsync(AccountResetPasswordRequest request) => recovery.ResetAsync(request, Context.RequestAborted);
    public Task<IResult> ForgotForBlazorAsync(AccountEmailRequest request) => recovery.ForgotAsync(request, Context.RequestAborted, supportsTwoFactor: true);
    public Task<IResult> ResetForBlazorAsync(AccountResetPasswordRequest request) => recovery.ResetAsync(request, Context.RequestAborted, supportsTwoFactor: true);
    public Task<IResult> LogoutAllAsync(AccountPasswordRequest request) => revocation.LogoutAllAsync(request, Context.User, Context.RequestAborted);
    public Task<IResult> ChangePasswordAsync(AccountChangePasswordRequest request) => passwordChanges.ChangePasswordAsync(request, Context.User, Context.RequestAborted);
    public Task<IResult> ChangeEmailAsync(AccountChangeEmailRequest request) => emailChanges.ChangeEmailAsync(request, Context.User, Context.RequestAborted);
    public Task<IResult> ConfirmEmailChangeAsync(AccountConfirmEmailChangeRequest request) => emailChanges.ConfirmEmailChangeAsync(request, Context.RequestAborted);
    public Task<IResult> ExportAsync(AccountPasswordRequest request) => exports.ExportAsync(request, Context.User, Context.RequestAborted);
    public Task<IResult> DeleteAsync(AccountPasswordRequest request) => deletions.DeleteAsync(request, Context.User, Context.RequestAborted);
}
