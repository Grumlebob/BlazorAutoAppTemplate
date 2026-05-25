using Microsoft.AspNetCore.Components;

namespace BlazorAutoApp.Client.Features.AppShell.Components;

public partial class RenderModeBadge
{
    [Parameter]
    public IComponentRenderMode? Assigned { get; set; }

    [Parameter]
    public string ConfiguredMode { get; set; } = "Interactive Auto";

    private string AssignedModeName => FormatRenderMode(Assigned ?? AssignedRenderMode) ?? "Static";

    private string CurrentRendererName =>
        RendererInfo.Name == "Static" && ConfiguredMode != "Static"
            ? "Static prerender"
            : RendererInfo.Name;

    private string InteractiveText => RendererInfo.IsInteractive ? "yes" : "no";

    private static string? FormatRenderMode(IComponentRenderMode? mode)
    {
        if (mode is null)
        {
            return null;
        }

        var name = mode.GetType().Name.Replace("RenderMode", "", StringComparison.Ordinal);
        return name switch
        {
            "InteractiveAuto" => "Interactive Auto",
            "InteractiveServer" => "Interactive Server",
            "InteractiveWebAssembly" => "Interactive WebAssembly",
            _ => name
        };
    }
}
