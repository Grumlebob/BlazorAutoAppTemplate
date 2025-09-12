using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Inspections.VerifyInspectionEmail;

[Collection("MediaTestCollection")]
public class VerifyInspectionEmailTests
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly IServiceScope _scope;
    private readonly AppDbContext _db;

    public VerifyInspectionEmailTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _db = _scope.ServiceProvider.GetRequiredService<AppDbContext>();
    }

    [Fact]
    public async Task Verify_And_Status_Work()
    {
        await _resetDatabase();

        var id = Guid.NewGuid();
        var password = "pass123";
        var (salt, hash) = HashPassword(password);
        // Seed required CompanyDetails row due to FK
        var company = new BlazorAutoApp.Core.Features.Inspections.StartHullInspectionEmail.CompanyDetail { Name = "Acme", Email = "x@y.z" };
        _db.CompanyDetails.Add(company);
        await _db.SaveChangesAsync();

        _db.Inspections.Add(new BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail.Inspection
        {
            Id = id,
            CompanyId = company.Id,
            PasswordSalt = salt,
            PasswordHash = hash,
            CreatedAtUtc = DateTime.UtcNow
        });
        await _db.SaveChangesAsync();

        // wrong password -> 400
        var bad = await _client.PostAsJsonAsync($"/api/inspection/{id}/verify", new VerifyInspectionPasswordRequest { Id = id, Password = "wrong" });
        Assert.Equal(HttpStatusCode.BadRequest, bad.StatusCode);

        // correct password -> 200 and status true
        var ok = await _client.PostAsJsonAsync($"/api/inspection/{id}/verify", new VerifyInspectionPasswordRequest { Id = id, Password = password });
        Assert.Equal(HttpStatusCode.OK, ok.StatusCode);

        var st = await _client.GetFromJsonAsync<InspectionStatusResponse>($"/api/inspection/{id}/status");
        Assert.NotNull(st);
        Assert.True(st!.Verified);
    }

    private static (string Salt, string Hash) HashPassword(string password)
    {
        var saltBytes = RandomNumberGenerator.GetBytes(16);
        var salt = Convert.ToBase64String(saltBytes);
        using var sha = SHA256.Create();
        var combined = Encoding.UTF8.GetBytes(password + ":" + salt);
        var hash = Convert.ToBase64String(sha.ComputeHash(combined));
        return (salt, hash);
    }
}
