using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Client.Services;
using BlazorAutoApp.Core.Features.Email;
using BlazorAutoApp.Core.Features.HullImages;

var builder = WebAssemblyHostBuilder.CreateDefault(args);

builder.Services.AddScoped(sp => new HttpClient
{
    BaseAddress = new Uri(builder.HostEnvironment.BaseAddress)
});

// Movies service for WASM after hydration
builder.Services.AddScoped<IMoviesApi, MoviesClientService>();
builder.Services.AddScoped<IHullImagesApi, HullImagesClientService>();
builder.Services.AddScoped<IEmailApi, SendEmailClientService>();

await builder.Build().RunAsync();
