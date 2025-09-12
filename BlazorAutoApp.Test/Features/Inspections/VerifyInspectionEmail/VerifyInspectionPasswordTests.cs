using System;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail;
using BlazorAutoApp.Test.TestingSetup;
using Xunit;

namespace BlazorAutoApp.Test.Features.Inspections.VerifyInspectionEmail;

[Collection("MediaTestCollection")]
public class VerifyInspectionPasswordTests
{
    private readonly WebAppFactory _factory;

    public VerifyInspectionPasswordTests(WebAppFactory factory) => _factory = factory;

    [Fact]
    public async Task Status_For_Unknown_Id_Is_NotVerified()
    {
        var res = await _factory.HttpClient.GetFromJsonAsync<InspectionStatusResponse>($"/api/inspection/{Guid.NewGuid()}/status");
        Assert.NotNull(res);
        Assert.False(res!.Verified);
    }
}
