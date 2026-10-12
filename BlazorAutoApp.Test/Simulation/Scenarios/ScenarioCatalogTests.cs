using System;
using System.Linq;
using BlazorAutoApp.Simulation.Scenarios;
using Xunit;

namespace BlazorAutoApp.Test.Simulation.Scenarios;

public sealed class ScenarioCatalogTests
{
    [Fact]
    public void BuildReadOnly_DoesNotGenerateRetiredBookDesignDemoPaths()
    {
        var context = new ScenarioContext(new Random(1729));
        var pageScenarios = ScenarioCatalog.BuildReadOnly()
            .Where(scenario => scenario.Category is ScenarioCategory.Page)
            .ToArray();

        Assert.NotEmpty(pageScenarios);
        foreach (var scenario in pageScenarios)
        {
            var path = scenario.PathFactory(context);

            Assert.False(string.IsNullOrWhiteSpace(path), $"{scenario.Name} returned no page path.");
            Assert.False(
                path!.StartsWith("/books/design-demos", StringComparison.OrdinalIgnoreCase),
                $"{scenario.Name} still targets a retired demo route.");
        }
    }
}
