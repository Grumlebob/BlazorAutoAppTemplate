using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.UseCases.GetInspectionFlow;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.UseCases.UpsertInspectionFlow;

namespace BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Contracts;

public interface IInspectionFlowApi
{
    Task<GetInspectionFlowResponse> GetAsync(Guid id, CancellationToken ct = default);
    Task<UpsertInspectionFlowResponse> UpsertAsync(UpsertInspectionFlowRequest req, CancellationToken ct = default);
}
