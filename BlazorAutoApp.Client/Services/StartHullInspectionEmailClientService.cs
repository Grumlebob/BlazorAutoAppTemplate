using System.Net;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Inspections.StartHullInspectionEmail;

namespace BlazorAutoApp.Client.Services;

public class StartHullInspectionEmailClientService(HttpClient http) : IStartHullInspectionEmailApi
{
    private readonly HttpClient _http = http;

    public async Task<GetCompaniesResponse> GetCompaniesAsync(CancellationToken ct = default)
    {
        var res = await _http.GetFromJsonAsync<GetCompaniesResponse>("api/start-hull-inspection-email/companies", ct);
        return res ?? new GetCompaniesResponse { Items = new() };
    }

    public async Task<StartHullInspectionResponse> StartAsync(StartHullInspectionRequest req, CancellationToken ct = default)
    {
        var httpRes = await _http.PostAsJsonAsync("api/start-hull-inspection-email/start", req, ct);
        StartHullInspectionResponse? payload = null;
        try { payload = await httpRes.Content.ReadFromJsonAsync<StartHullInspectionResponse>(cancellationToken: ct); } catch { }
        if (httpRes.StatusCode is HttpStatusCode.Accepted or HttpStatusCode.OK)
            return payload ?? new StartHullInspectionResponse { Success = true };
        return payload ?? new StartHullInspectionResponse { Success = false, Error = await httpRes.Content.ReadAsStringAsync(ct) };
    }

    public async Task<ActivateInspectionResponse> ActivateAsync(Guid id, CancellationToken ct = default)
    {
        var res = await _http.PostAsync($"api/start-hull-inspection-email/activate/{id}", content: null, ct);
        ActivateInspectionResponse? payload = null;
        try { payload = await res.Content.ReadFromJsonAsync<ActivateInspectionResponse>(cancellationToken: ct); } catch { }
        if (res.StatusCode is HttpStatusCode.OK)
            return payload ?? new ActivateInspectionResponse { Success = true };
        return payload ?? new ActivateInspectionResponse { Success = false, Error = await res.Content.ReadAsStringAsync(ct) };
    }
}
