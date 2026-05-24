using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.UseCases.GetVesselPartDetails;
using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.UseCases.UpsertVesselPartDetails;

namespace BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Contracts;

public interface IVesselPartDetailsApi
{
    Task<GetVesselPartDetailsResponse> GetAsync(int vesselPartId, CancellationToken ct = default);
    Task<UpsertVesselPartDetailsResponse> UpsertAsync(UpsertVesselPartDetailsRequest req, CancellationToken ct = default);
}
