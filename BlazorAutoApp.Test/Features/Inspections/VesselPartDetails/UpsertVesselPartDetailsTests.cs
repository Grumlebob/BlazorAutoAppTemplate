using System;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Inspections.Inspection;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;
using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace BlazorAutoApp.Test.Features.Inspections.VesselPartDetails;

[Collection("MediaTestCollection")]
public class UpsertVesselPartDetailsTests
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public UpsertVesselPartDetailsTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task Upsert_Then_Get_Returns_Updated_Details()
    {
        await _resetDatabase();

        // Ensure an inspection exists
        await using var db = await _dbFactory.CreateDbContextAsync();
        var inspId = Guid.NewGuid();
        db.Inspections.Add(new Inspection
        {
            Id = inspId,
            CreatedAtUtc = DateTime.UtcNow
        });
        db.SaveChanges();

        // Create vessel part via inspection flow
        var upsertFlow = await _client.PostAsJsonAsync($"/api/inspection-flow/{inspId}", new UpsertInspectionFlowRequest
        {
            Id = inspId,
            VesselName = "Vessel Z",
            InspectionType = InspectionType.GoProInspection,
            VesselParts = [new InspectionVesselPartDto { PartCode = "bow::Port" }]
        });
        upsertFlow.EnsureSuccessStatusCode();

        var flow = await _client.GetFromJsonAsync<GetInspectionFlowResponse>($"/api/inspection-flow/{inspId}");
        Assert.NotNull(flow);
        var vpId = flow!.VesselParts.First().Id!.Value;

        // Upsert details for that vessel part
        var req = new UpsertVesselPartDetailsRequest
        {
            InspectionVesselPartId = vpId,
            Fouling =
            {
                new FoulingObservationDto { FoulingType = FoulingType.Algae, IsPresent = true, CoveragePercent = 30 },
                new FoulingObservationDto { FoulingType = FoulingType.Barnacles, IsPresent = false, CoveragePercent = null }
            },
            Coating = new CoatingConditionDto { IntactPercent = 85, Peeling = false, Blisters = true, Scratching = false },
            Hull = new HullConditionDto { IntegrityPercent = 90, Corrosion = false, Dents = true, Cracks = false },
            Rating = new HullRatingDto { Rating = HullRatingValue.Light, Rationale = "Minor fouling" },
            Notes = "Under port side observation"
        };

        var put = await _client.PutAsJsonAsync($"/api/vessel-part-details/{vpId}", req);
        put.EnsureSuccessStatusCode();

        // Verify via GET
        var details = await _client.GetFromJsonAsync<GetVesselPartDetailsResponse>($"/api/vessel-part-details/{vpId}");
        Assert.NotNull(details);
        Assert.Equal(vpId, details!.InspectionVesselPartId);
        Assert.Equal(85, details.Coating.IntactPercent);
        Assert.True(details.Hull.Dents);
        Assert.Equal(HullRatingValue.Light, details.Rating.Rating);
        Assert.Equal("Under port side observation", details.Notes);
        var algae = details.Fouling.First(f => f.FoulingType == FoulingType.Algae);
        Assert.True(algae.IsPresent);
        Assert.Equal(30, algae.CoveragePercent);
    }
}
