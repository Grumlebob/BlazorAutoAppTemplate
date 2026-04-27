using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Inspections.Inspection;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace BlazorAutoApp.Test.Features.Inspections.InspectionFlow;

[Collection("MediaTestCollection")]
public class UpsertInspectionFlowTests
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public UpsertInspectionFlowTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task Upsert_Bootstraps_When_Inspection_Not_Found()
    {
        await _resetDatabase();
        var id = Guid.NewGuid();
        var req = new UpsertInspectionFlowRequest { Id = id, VesselName = "X", InspectionType = InspectionType.GoProInspection };
        var res = await _client.PostAsJsonAsync($"/api/inspection-flow/{id}", req);
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);

        await using var db = await _dbFactory.CreateDbContextAsync();
        var insp = await db.Inspections.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id);
        Assert.NotNull(insp);
    }

    [Fact]
    public async Task Upsert_Preserves_VesselPart_Ids_By_PartCode()
    {
        await _resetDatabase();
        var id = Guid.NewGuid();
        await SeedInspectionAsync(id);

        var req = new UpsertInspectionFlowRequest
        {
            Id = id,
            VesselName = "VesselA",
            InspectionType = InspectionType.GoProInspection,
            VesselParts =
            [
                new InspectionVesselPartDto { PartCode = "bow::Port" },
                new InspectionVesselPartDto { PartCode = "bow::Starboard" }
            ]
        };
        var up1 = await _client.PostAsJsonAsync($"/api/inspection-flow/{id}", req);
        up1.EnsureSuccessStatusCode();
        var flow1 = await _client.GetFromJsonAsync<GetInspectionFlowResponse>($"/api/inspection-flow/{id}");
        Assert.NotNull(flow1);
        var p1 = flow1!.VesselParts.First(v => v.PartCode == "bow::Port").Id;
        var p2 = flow1!.VesselParts.First(v => v.PartCode == "bow::Starboard").Id;
        Assert.True(p1.HasValue && p2.HasValue);

        // Reorder and resubmit; ids should be preserved
        req.VesselParts.Reverse();
        var up2 = await _client.PostAsJsonAsync($"/api/inspection-flow/{id}", req);
        up2.EnsureSuccessStatusCode();
        var flow2 = await _client.GetFromJsonAsync<GetInspectionFlowResponse>($"/api/inspection-flow/{id}");
        var p1b = flow2!.VesselParts.First(v => v.PartCode == "bow::Port").Id;
        var p2b = flow2!.VesselParts.First(v => v.PartCode == "bow::Starboard").Id;
        Assert.Equal(p1, p1b);
        Assert.Equal(p2, p2b);

        // Remove one part; remaining id should stay
        req.VesselParts = [new InspectionVesselPartDto { PartCode = "bow::Port" }];
        var up3 = await _client.PostAsJsonAsync($"/api/inspection-flow/{id}", req);
        up3.EnsureSuccessStatusCode();
        var flow3 = await _client.GetFromJsonAsync<GetInspectionFlowResponse>($"/api/inspection-flow/{id}");
        var p1c = flow3!.VesselParts.First(v => v.PartCode == "bow::Port").Id;
        Assert.Equal(p1, p1c);
    }
    

    private async Task SeedInspectionAsync(Guid id)
    {
        // minimal seed: inspection record must exist
        await using var db = await _dbFactory.CreateDbContextAsync();
        db.Inspections.Add(new Inspection
        {
            Id = id,
            CreatedAtUtc = DateTime.UtcNow
        });
        await db.SaveChangesAsync();
    }
}
