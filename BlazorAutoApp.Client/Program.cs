using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using BlazorAutoApp.Client.Features.Inspections.HullImages;
using BlazorAutoApp.Client.Features.Inspections.InspectionFlow;
using BlazorAutoApp.Client.Features.Inspections.VesselPartDetails;
using BlazorAutoApp.Client.Features.Movies;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Core.Features.Inspections.HullImages;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow;
using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails;

var builder = WebAssemblyHostBuilder.CreateDefault(args);

builder.Services.AddScoped(sp => new HttpClient
{
    BaseAddress = new Uri(builder.HostEnvironment.BaseAddress)
});

// Movies service for WASM after hydration
builder.Services.AddScoped<IMoviesApi, MoviesClientService>();
builder.Services.AddScoped<IHullImagesApi, HullImagesClientService>();
builder.Services.AddScoped<IInspectionFlowApi, InspectionFlowClientService>();
builder.Services.AddScoped<IVesselPartDetailsApi, VesselPartDetailsClientService>();

await builder.Build().RunAsync();

