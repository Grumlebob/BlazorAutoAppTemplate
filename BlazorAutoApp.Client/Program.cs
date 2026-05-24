using BlazorAutoApp.Client.Features.IdentityShowcase;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using BlazorAutoApp.Client.Features.Inspections.HullImages;
using BlazorAutoApp.Client.Features.Inspections.InspectionFlow;
using BlazorAutoApp.Client.Features.Inspections.VesselPartDetails;
using BlazorAutoApp.Client.Features.Movies;
using BlazorAutoApp.Core.Features.IdentityShowcase.Contracts;
using BlazorAutoApp.Core.Features.Movies.Contracts;
using BlazorAutoApp.Core.Features.Inspections.HullImages.Contracts;
using BlazorAutoApp.Core.Features.Inspections.InspectionFlow.Contracts;
using BlazorAutoApp.Core.Features.Inspections.VesselPartDetails.Contracts;

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
builder.Services.AddScoped<IIdentityShowcaseApi, IdentityShowcaseClientService>();

await builder.Build().RunAsync();

