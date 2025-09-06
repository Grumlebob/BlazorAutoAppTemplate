using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Microsoft.AspNetCore.Components;
using Xunit;

namespace BlazorAutoApp.Test.Architecture;

public class HttpClientUsageTests
{
    [Fact]
    public void ServerAssembly_HasNo_HttpClient_InjectionOrSurface()
    {
        var server = typeof(BlazorAutoApp.Features.Movies.MoviesServerService).Assembly;
        var offenders = new List<string>();

        foreach (var t in server.GetTypes())
        {
            // Fields
            foreach (var f in t.GetFields(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
                if (ContainsHttpClient(f.FieldType)) offenders.Add($"{t.FullName} field {f.Name}");

            // Properties
            foreach (var p in t.GetProperties(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
                if (ContainsHttpClient(p.PropertyType)) offenders.Add($"{t.FullName} property {p.Name}");

            // Methods
            foreach (var m in t.GetMethods(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (ContainsHttpClient(m.ReturnType)) offenders.Add($"{t.FullName} method {m.Name} return");
                foreach (var param in m.GetParameters())
                    if (ContainsHttpClient(param.ParameterType)) offenders.Add($"{t.FullName} method {m.Name} param {param.Name}");
            }

            // Constructors
            foreach (var c in t.GetConstructors(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
                foreach (var param in c.GetParameters())
                    if (ContainsHttpClient(param.ParameterType)) offenders.Add($"{t.FullName} ctor param {param.Name}");
        }

        Assert.True(offenders.Count == 0, "Server must not use HttpClient directly:\n" + string.Join("\n", offenders));
    }

    private static bool ContainsHttpClient(Type? type)
    {
        if (type is null) return false;
        if (type.FullName == "System.Net.Http.HttpClient") return true;
        if (type.IsGenericType) return type.GetGenericArguments().Any(ContainsHttpClient);
        if (type.HasElementType) return ContainsHttpClient(type.GetElementType());
        return false;
    }

    [Fact]
    public void BlazorComponents_DoNotInject_HttpClient()
    {
        var client = typeof(BlazorAutoApp.Client.Services.MoviesClientService).Assembly;
        var offenders = new List<string>();
        var componentType = typeof(ComponentBase);
        const string injectAttrName = "InjectAttribute";

        foreach (var t in client.GetTypes().Where(tt => componentType.IsAssignableFrom(tt)))
        {
            foreach (var p in t.GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                var hasInject = p.GetCustomAttributes(inherit: true).Any(a => a.GetType().Name == injectAttrName);
                if (hasInject && p.PropertyType.FullName == "System.Net.Http.HttpClient")
                    offenders.Add($"{t.FullName} property {p.Name}");
            }
        }

        Assert.True(offenders.Count == 0, "Blazor components must not inject HttpClient directly:\n" + string.Join("\n", offenders));
    }
}

