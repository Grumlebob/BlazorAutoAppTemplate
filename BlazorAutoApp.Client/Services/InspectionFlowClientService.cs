using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;

namespace BlazorAutoApp.Client.Services;

public class InspectionFlowClientService(HttpClient http) : IInspectionFlowApi
{
    private readonly HttpClient _http = http;

    public async Task<GetInspectionFlowResponse> GetAsync(Guid id, CancellationToken ct = default)
    {
        var res = await _http.GetFromJsonAsync<GetInspectionFlowResponse>($"api/inspection-flow/{id}", ct);
        return res ?? new GetInspectionFlowResponse { Id = id };
    }

    public async Task<UpsertInspectionFlowResponse> UpsertAsync(UpsertInspectionFlowRequest req, CancellationToken ct = default)
    {
        var res = await _http.PostAsJsonAsync($"api/inspection-flow/{req.Id}", req, ct);
        return (await res.Content.ReadFromJsonAsync<UpsertInspectionFlowResponse>(cancellationToken: ct))
               ?? new UpsertInspectionFlowResponse { Success = false, Error = "No response" };
    }

    public async Task<GetVesselsResponse> GetVesselsAsync(CancellationToken ct = default)
    {
        var res = await _http.GetFromJsonAsync<GetVesselsResponse>("api/inspection-flow/vessels", ct);
        return res ?? new GetVesselsResponse { Items = new() };
    }
}
