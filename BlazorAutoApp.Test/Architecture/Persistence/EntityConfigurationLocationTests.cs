using System;
using System.Linq;
using System.Reflection;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Xunit;
using BlazorAutoApp.Test.Architecture.Support;

namespace BlazorAutoApp.Test.Architecture.Persistence;

public class EntityConfigurationLocationTests
{
    [Fact]
    public void AppDbContext_DbSets_Use_Core_Domain_Entities()
    {
        var offenders = typeof(AppDbContext)
            .GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.DeclaredOnly)
            .Where(p => p.PropertyType.IsGenericType && p.PropertyType.GetGenericTypeDefinition() == typeof(DbSet<>))
            .Select(p => new
            {
                DbSet = p.Name,
                Entity = p.PropertyType.GetGenericArguments()[0]
            })
            .Where(x => x.Entity.Namespace is null
                     || !x.Entity.Namespace.StartsWith("BlazorAutoApp.Core.Features.", StringComparison.Ordinal)
                     || !x.Entity.Namespace.Split('.').Contains("Domain", StringComparer.Ordinal))
            .Select(x => $"{x.DbSet}: {x.Entity.FullName}")
            .OrderBy(x => x)
            .ToList();

        Assert.True(offenders.Count == 0,
            "AppDbContext feature DbSets should use Core Domain entities:\n" + string.Join("\n", offenders));
    }

    [Fact]
    public void EntityConfigurations_LiveUnder_Feature_Persistence_Namespaces()
    {
        var configTypes = ArchitectureAssemblies.Server.GetTypes()
            .Where(t => t.IsClass && !t.IsAbstract)
            .Where(t => t.GetInterfaces()
                .Any(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IEntityTypeConfiguration<>)))
            .ToList();

        // Ensure at least one exists (Books config in this template)
        Assert.NotEmpty(configTypes);

        var offenders = configTypes
            .Where(t => t.Namespace is null
                     || !t.Namespace.StartsWith("BlazorAutoApp.Features.", StringComparison.Ordinal)
                     || !t.Namespace.Split('.').Contains("Persistence", StringComparer.Ordinal))
            .Select(t => t.FullName)
            .ToList();

        if (offenders.Count > 0)
        {
            var root = SourceSearch.GetRepoRoot();
            var hints = configTypes
                .Where(t => t.Namespace is null
                         || !t.Namespace.StartsWith("BlazorAutoApp.Features.", StringComparison.Ordinal)
                         || !t.Namespace.Split('.').Contains("Persistence", StringComparer.Ordinal))
                .SelectMany(t => SourceSearch.FindTypeHints(root, "BlazorAutoApp", t))
                .ToList();

            var msg = "EntityTypeConfiguration classes must be under BlazorAutoApp.Features.*.Persistence:\n"
                      + string.Join("\n", offenders)
                      + (hints.Count > 0 ? "\n\nSource locations:\n" + string.Join("\n", hints) : string.Empty);
            Assert.Fail(msg);
        }
    }

    [Fact]
    public void EntityConfigurations_Target_Core_Domain_Entities()
    {
        var offenders = ArchitectureAssemblies.Server.GetTypes()
            .Where(t => t.IsClass && !t.IsAbstract)
            .SelectMany(t => t.GetInterfaces()
                .Where(i => i.IsGenericType && i.GetGenericTypeDefinition() == typeof(IEntityTypeConfiguration<>))
                .Select(i => new
                {
                    Configuration = t,
                    Entity = i.GetGenericArguments()[0]
                }))
            .Where(x => x.Entity.Namespace is null
                     || !x.Entity.Namespace.StartsWith("BlazorAutoApp.Core.Features.", StringComparison.Ordinal)
                     || !x.Entity.Namespace.Split('.').Contains("Domain", StringComparer.Ordinal))
            .Select(x => $"{x.Configuration.FullName} -> {x.Entity.FullName}")
            .OrderBy(x => x)
            .ToList();

        Assert.True(offenders.Count == 0,
            "EntityTypeConfiguration classes should target Core Domain entities:\n" + string.Join("\n", offenders));
    }
}
