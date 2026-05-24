using System.Reflection;
using BlazorAutoApp;
using BlazorAutoApp.Client;
using BlazorAutoApp.Core;
using BlazorAutoApp.Test.TestingSetup;

namespace BlazorAutoApp.Test.Architecture;

internal static class ArchitectureAssemblies
{
    public static Assembly Core => typeof(CoreAssemblyMarker).Assembly;
    public static Assembly Server => typeof(ServerAssemblyMarker).Assembly;
    public static Assembly Client => typeof(ClientAssemblyMarker).Assembly;
    public static Assembly Tests => typeof(WebAppFactory).Assembly;
}
