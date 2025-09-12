namespace BlazorAutoApp.Features.Inspections.HullImages;

public interface ITusResultRegistry
{
    void Set(Guid correlationId, int imageId);
    bool TryGet(Guid correlationId, out int imageId);
}

public class TusResultRegistry : ITusResultRegistry
{
    private readonly ConcurrentDictionary<Guid, int> _map = new();
    public void Set(Guid correlationId, int imageId) => _map[correlationId] = imageId;
    public bool TryGet(Guid correlationId, out int imageId) => _map.TryGetValue(correlationId, out imageId);
}
