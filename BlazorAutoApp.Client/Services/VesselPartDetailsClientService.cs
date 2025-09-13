using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails;

namespace BlazorAutoApp.Client.Services;

public class VesselPartDetailsClientService(HttpClient http) : IVesselPartDetailsApi
{
    private readonly HttpClient _http = http;

    public async Task<GetVesselPartDetailsResponse> GetAsync(int vesselPartId, CancellationToken ct = default)
    {
        var res = await _http.GetFromJsonAsync<GetVesselPartDetailsResponse>($"api/vessel-part-details/{vesselPartId}", ct);
        return res ?? new GetVesselPartDetailsResponse { InspectionVesselPartId = vesselPartId };
    }

    public async Task<UpsertVesselPartDetailsResponse> UpsertAsync(UpsertVesselPartDetailsRequest req, CancellationToken ct = default)
    {
        var res = await _http.PutAsJsonAsync($"api/vessel-part-details/{req.InspectionVesselPartId}", req, ct);
        return (await res.Content.ReadFromJsonAsync<UpsertVesselPartDetailsResponse>(cancellationToken: ct))
               ?? new UpsertVesselPartDetailsResponse { Success = false, Error = "No response" };
    }
}

