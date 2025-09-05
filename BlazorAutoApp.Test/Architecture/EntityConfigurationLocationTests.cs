using System;
using System.Linq;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class EntityConfigurationLocationTests
{
    [Fact]
    public void EntityConfigurations_LiveUnder_FeaturesNamespace()
    {
        var server = typeof(BlazorAutoApp.Features.Movies.MoviesServerService).Assembly;

        var configTypes = server.GetTypes()
            .Where(t => t.IsClass && !t.IsAbstract)
            .Where(t => t.GetInterfaces()
                .Any(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IEntityTypeConfiguration<>)))
            .ToList();

        // Ensure at least one exists (Movies config in this template)
        Assert.NotEmpty(configTypes);

        var offenders = configTypes
            .Where(t => t.Namespace is null || !t.Namespace.StartsWith("BlazorAutoApp.Features.", StringComparison.Ordinal))
            .Select(t => t.FullName)
            .ToList();

        Assert.True(offenders.Count == 0, "EntityTypeConfiguration classes must be under BlazorAutoApp.Features.*:\n" + string.Join("\n", offenders));
    }
}

