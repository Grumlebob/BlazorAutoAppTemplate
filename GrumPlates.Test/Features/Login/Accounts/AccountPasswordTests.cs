using System.ComponentModel.DataAnnotations;
using System.Security.Cryptography;
using GrumPlates.Core.Features.Login.UseCases.Shared;
using GrumPlates.Features.Login.Account;
using GrumPlates.Features.Login.Accounts;
using GrumPlates.Features.Login.Accounts.Security;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Xunit;

namespace GrumPlates.Test.Features.Login.Accounts;

public sealed class AccountPasswordTests
{
    [Theory]
    [InlineData(14, false)]
    [InlineData(15, true)]
    [InlineData(128, true)]
    [InlineData(129, false)]
    public void NewPassword_CountsUnicodeCodePoints(int count, bool expected)
    {
        Assert.Equal(expected, Validate(new string('x', count)).Succeeded);
        Assert.Equal(expected, Validate(string.Concat(Enumerable.Repeat("😀", count))).Succeeded);
    }

    [Theory]
    [InlineData("a passphrase with spaces")]
    [InlineData("  keep surrounding spaces  ")]
    [InlineData("Prefix password suffix")]
    [InlineData("á combining characters allowed")]
    public void NewPassword_AllowsSpacesAndWholeWordSubstrings(string password) => Assert.True(Validate(password).Succeeded);

    [Fact]
    public void NewPassword_RefusesInvalidUtf16AndControlCharacters()
    {
        foreach (var invalid in new[] { '\uD800', '\uDC00', '\0', '\r', '\n', '\t', '\u0085' })
        {
            Assert.False(Validate("a sufficiently long value" + invalid).Succeeded);
        }
    }

    [Theory]
    [InlineData("xxxxxxxxxxxxxx", false)]
    [InlineData("xxxxxxxxxxxxxxx", true)]
    [InlineData("😀😀😀😀😀😀😀😀😀😀😀😀😀😀", false)]
    [InlineData("😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀", true)]
    public void BlazorFormPasswordAttribute_UsesUnicodeCodePointBounds(string password, bool expected)
    {
        Assert.Equal(expected, ValidateFormPassword(password));
    }

    [Fact]
    public void BlazorFormPasswordAttribute_EnforcesTransportAndUnicodeSafety()
    {
        Assert.True(ValidateFormPassword(string.Concat(Enumerable.Repeat("😀", 128))));
        Assert.False(ValidateFormPassword(string.Concat(Enumerable.Repeat("😀", 129))));
        Assert.False(ValidateFormPassword("a sufficiently long value\n"));
        Assert.False(ValidateFormPassword("a sufficiently long value\uD800"));
    }

    [Fact]
    public void BlazorFormPasswordAttribute_PreservesLegacyDisabledPolicy()
    {
        var disabled = new PolicyFormPasswordModel("legacy");
        disabled.SetAccountPasswordPolicy(enabled: false);
        var enabled = new PolicyFormPasswordModel("legacy");
        enabled.SetAccountPasswordPolicy(enabled: true);

        Assert.True(ValidateModelPassword(disabled));
        Assert.False(ValidateModelPassword(enabled));
    }

    [Theory]
    [InlineData("films+pic+galeries")]
    [InlineData("FILMS+PIC+GALERIES")]
    [InlineData("identity@example.test")]
    [InlineData("IDENTITY@EXAMPLE.TEST")]
    [InlineData("The Example Application")]
    public void NewPassword_RefusesCompleteCommonAndContextValues(string password)
    {
        Assert.Equal("PasswordTooCommon", Assert.Single(Validate(password).Errors).Code);
    }

    [Fact]
    public void EmbeddedResource_HasPinnedHashSizeAndSourceLineCount()
    {
        using var resource = typeof(AccountOptions).Assembly.GetManifestResourceStream(AccountPasswordValidator.ResourceName);
        Assert.NotNull(resource);
        using var content = new MemoryStream();
        resource.CopyTo(content);
        Assert.Equal(73026, content.Length);
        Assert.True(content.Length < 256 * 1024);
        Assert.Equal(AccountPasswordValidator.ResourceSha256, Convert.ToHexStringLower(SHA256.HashData(content.ToArray())));
        using var reader = new StringReader(System.Text.Encoding.UTF8.GetString(content.ToArray()));
        var lines = 0;
        while (reader.ReadLine() is not null) lines++;
        Assert.Equal(10001, lines);
    }

    [Fact]
    public void DtoTransport_Allows128NonBmpCodePointsAndLegacyShortProof()
    {
        var newPassword = new AccountChangePasswordRequest { Password = "old", NewPassword = string.Concat(Enumerable.Repeat("😀", 128)) };
        Assert.True(Validator.TryValidateObject(newPassword, new ValidationContext(newPassword), [], validateAllProperties: true));
        var login = new AccountLoginRequest { Email = "identity@example.test", Password = "old" };
        Assert.True(Validator.TryValidateObject(login, new ValidationContext(login), [], validateAllProperties: true));
        login.Password = new string(' ', 15);
        Assert.True(Validate(login.Password).Succeeded);
        Assert.True(Validator.TryValidateObject(login, new ValidationContext(login), [], validateAllProperties: true));
        login.Password = "";
        Assert.False(Validator.TryValidateObject(login, new ValidationContext(login), [], validateAllProperties: true));
    }

    [Fact]
    public void LoginHashVerification_DoesNotApplyNewPasswordRulesOrTrimContents()
    {
        var user = new ApplicationUser();
        var hasher = new PasswordHasher<ApplicationUser>();
        var hash = hasher.HashPassword(user, " old ");
        Assert.False(Validate(" old ").Succeeded);
        Assert.Equal(PasswordVerificationResult.Success, hasher.VerifyHashedPassword(user, hash, " old "));
        Assert.Equal(PasswordVerificationResult.Failed, hasher.VerifyHashedPassword(user, hash, "old"));
    }

    [Fact]
    public void EnabledIdentity_UsesOnlyCodePointValidatorAndFixedLockoutAndTokenSettings()
    {
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> { ["Accounts:Enabled"] = "true" }).Build();
        var services = new ServiceCollection();
        services.AddIdentityBackend();
        services.AddAccountFeature(configuration, new Account.LocalLoginAccountSeedingRulesTests.StubEnvironment("Testing"));
        Assert.Single(services, service => service.ServiceType == typeof(IPasswordValidator<ApplicationUser>));
        Assert.Equal(typeof(AccountPasswordValidator), services.Single(service => service.ServiceType == typeof(IPasswordValidator<ApplicationUser>)).ImplementationType);
        using var provider = services.BuildServiceProvider();
        var identity = provider.GetRequiredService<IOptions<IdentityOptions>>().Value;
        Assert.Equal(5, identity.Lockout.MaxFailedAccessAttempts);
        Assert.Equal(TimeSpan.FromMinutes(15), identity.Lockout.DefaultLockoutTimeSpan);
        Assert.Equal(TimeSpan.FromHours(1), provider.GetRequiredService<IOptions<DataProtectionTokenProviderOptions>>().Value.TokenLifespan);
    }

    [Fact]
    public void SeedPassword_IsValidatedBeforeDatabaseAccessEvenIfAdminMayAlreadyExist()
    {
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["Accounts:Enabled"] = "true",
            ["Accounts:AdminSeed:Enabled"] = "true",
            ["Accounts:AdminSeed:Email"] = "identity@example.test",
            ["Accounts:AdminSeed:Password"] = "short"
        }).Build();
        var error = Assert.Throws<OptionsValidationException>(() => new ServiceCollection().AddAccountFeature(configuration,
            new Account.LocalLoginAccountSeedingRulesTests.StubEnvironment("Testing")));
        Assert.Contains("Accounts:AdminSeed:Password", error.Message);
        Assert.DoesNotContain("short", error.Message);
    }

    private static IdentityResult Validate(string password) =>
        AccountPasswordValidator.ValidateCandidate(password, "identity@example.test", "The Example Application");

    private static bool ValidateFormPassword(string password)
    {
        var model = new FormPasswordModel { Password = password };
        return ValidateModelPassword(model);
    }

    private static bool ValidateModelPassword(object model)
    {
        var property = model.GetType().GetProperty("Password")!;
        var context = new ValidationContext(model) { MemberName = property.Name };
        return Validator.TryValidateProperty(property.GetValue(model), context, []);
    }

    private sealed class FormPasswordModel
    {
        [AccountPasswordLength]
        public string Password { get; init; } = "";
    }

    private sealed class PolicyFormPasswordModel(string password) : AccountPasswordPolicyInputModel
    {
        [AccountPasswordLength]
        public string Password { get; } = password;
    }
}
