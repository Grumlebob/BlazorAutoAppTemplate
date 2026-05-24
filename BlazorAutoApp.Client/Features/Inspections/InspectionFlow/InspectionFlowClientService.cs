using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Contracts;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.UseCases.GetInspectionFlow;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.UseCases.UpsertInspectionFlow;

namespace BlazorAutoApp.Client.Features.Inspections.InspectionFlow;

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
}
