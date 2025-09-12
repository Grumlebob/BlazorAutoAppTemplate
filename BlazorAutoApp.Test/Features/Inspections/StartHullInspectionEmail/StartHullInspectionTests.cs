using System;
using System.Linq;
using System.Net;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Inspections.StartHullInspectionEmail;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Inspections.StartHullInspectionEmail;

[Collection("MediaTestCollection")]
public class StartHullInspectionTests
{
    private readonly WebAppFactory _factory;
    private readonly AppDbContext _db;

    public StartHullInspectionTests(WebAppFactory factory)
    {
        _factory = factory;
        var scope = factory.Services.CreateScope();
        _db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    }

    [Fact]
    public async Task GetCompanies_And_Start_Returns_Accepted()
    {
        // ensure at least one company exists (Program seeds some; but guard anyway)
        if (!_db.CompanyDetails.Any())
        {
            _db.CompanyDetails.Add(new CompanyDetail { Name = "AcmeCo", Email = "acme@example.com" });
            await _db.SaveChangesAsync();
        }

        var companies = await _factory.HttpClient.GetFromJsonAsync<GetCompaniesResponse>("/api/start-hull-inspection-email/companies");
        Assert.NotNull(companies);
        Assert.NotEmpty(companies!.Items);

        var companyId = companies.Items.First().Id;
        var res = await _factory.HttpClient.PostAsJsonAsync("/api/start-hull-inspection-email/start", new StartHullInspectionRequest { CompanyId = companyId });
        Assert.Equal(HttpStatusCode.Accepted, res.StatusCode);
    }
}
