using System.Reflection;
using GrumPlates.Client;
using GrumPlates.Core;
using GrumPlates.Test.TestSupport.Integration;

namespace GrumPlates.Test.Architecture.Support;

internal static class ArchitectureAssemblies
{
    public static Assembly Core => typeof(CoreAssemblyMarker).Assembly;
    public static Assembly Server => typeof(ServerAssemblyMarker).Assembly;
    public static Assembly Client => typeof(ClientAssemblyMarker).Assembly;
    public static Assembly Tests => typeof(WebAppFactory).Assembly;
}
