using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Inspections.VerifyInspectionEmail;

namespace BlazorAutoApp.Client.Services;

public class InspectionClientService(HttpClient http) : IVerifyInspectionEmailApi
{
    private readonly HttpClient _http = http;

    public async Task<VerifyInspectionPasswordResponse> VerifyPasswordAsync(VerifyInspectionPasswordRequest req, CancellationToken ct = default)
    {
        var res = await _http.PostAsJsonAsync($"api/inspection/{req.Id}/verify", req, ct);
        return (await res.Content.ReadFromJsonAsync<VerifyInspectionPasswordResponse>(cancellationToken: ct))
               ?? new VerifyInspectionPasswordResponse { Success = false, Error = "No response" };
    }

    public async Task<InspectionStatusResponse> GetStatusAsync(Guid id, CancellationToken ct = default)
    {
        var res = await _http.GetFromJsonAsync<InspectionStatusResponse>($"api/inspection/{id}/status", ct);
        return res ?? new InspectionStatusResponse { Verified = false, CompanyId = 0 };
    }
}
