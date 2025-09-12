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
}
