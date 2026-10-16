namespace BlazorAutoApp.Features.Login.Account;

internal abstract class AccountPasswordPolicyInputModel
{
    internal bool EnforceAccountPasswordPolicy { get; private set; }

    internal void SetAccountPasswordPolicy(bool enabled) => EnforceAccountPasswordPolicy = enabled;
}
